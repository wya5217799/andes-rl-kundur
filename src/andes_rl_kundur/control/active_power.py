"""Energy-feasible active-power contracts for the R272 authority gate."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PowerProjection:
    """Auditable result of one active-power projection."""

    requested_power_system_pu: np.ndarray
    commanded_power_system_pu: np.ndarray
    saturation_reasons: tuple[tuple[str, ...], ...]


class DroopPIActivePowerController:
    """Equal-sharing common-frequency droop plus integral restoration."""

    def __init__(
        self,
        *,
        device_count: int,
        nominal_frequency_hz: float,
        kp_system_pu_per_hz_per_device: float,
        ki_system_pu_per_hz_s_per_device: float,
    ) -> None:
        self.device_count = device_count
        self.nominal_frequency_hz = nominal_frequency_hz
        self.kp = kp_system_pu_per_hz_per_device
        self.ki = ki_system_pu_per_hz_s_per_device
        self.reset()

    def reset(self) -> None:
        self._integral_power_system_pu = 0.0

    def act(
        self,
        *,
        frequencies_hz: list[float] | np.ndarray,
        dt_seconds: float,
        previous_projection: PowerProjection | None = None,
    ) -> np.ndarray:
        """Return one equal request per device from physical-Hz input."""
        common_frequency_hz = float(np.mean(np.asarray(frequencies_hz, dtype=float)))
        error_hz = self.nominal_frequency_hz - common_frequency_hz
        integration_blocked = False
        if previous_projection is not None:
            saturated = not np.allclose(
                previous_projection.commanded_power_system_pu,
                previous_projection.requested_power_system_pu,
            )
            previous_direction = float(
                np.mean(previous_projection.requested_power_system_pu)
            )
            integration_blocked = saturated and error_hz * previous_direction > 0.0
        if not integration_blocked:
            self._integral_power_system_pu += self.ki * error_hz * dt_seconds
        request = self.kp * error_hz + self._integral_power_system_pu
        return np.full(self.device_count, request, dtype=float)


@dataclass(frozen=True)
class EnergyFeasibleBESSContract:
    """Physical and per-unit contract for identical aggregated BESS devices."""

    system_mva: float
    device_count: int
    modules_per_device: int
    module_power_mva: float
    module_energy_mwh: float
    soc_initial: float
    soc_min: float
    soc_max: float
    charge_efficiency: float
    discharge_efficiency: float
    full_scale_ramp_seconds: float
    active_current_lag_seconds: float
    source_ids: tuple[str, ...]
    active_current_limit_device_pu: float = 1.0

    def __post_init__(self) -> None:
        if not self.source_ids or any(not source.strip() for source in self.source_ids):
            raise ValueError("source_ids must contain traceable non-empty identifiers")
        if not 0.0 <= self.soc_min < self.soc_initial < self.soc_max <= 1.0:
            raise ValueError("require 0 <= soc_min < soc_initial < soc_max <= 1")

    @property
    def device_power_mva(self) -> float:
        return self.modules_per_device * self.module_power_mva

    @property
    def device_energy_mwh(self) -> float:
        return self.modules_per_device * self.module_energy_mwh

    @property
    def device_power_limit_system_pu(self) -> float:
        return self.device_power_mva / self.system_mva

    @property
    def device_ramp_limit_system_pu_per_s(self) -> float:
        return self.device_power_limit_system_pu / self.full_scale_ramp_seconds

    @property
    def initial_discharge_headroom_mwh(self) -> float:
        return self.device_energy_mwh * (self.soc_initial - self.soc_min)

    @property
    def initial_charge_headroom_mwh(self) -> float:
        return self.device_energy_mwh * (self.soc_max - self.soc_initial)

    def feasible_power_bounds(
        self,
        *,
        previous_power_system_pu: list[float] | np.ndarray,
        soc: list[float] | np.ndarray,
        voltage_pu: list[float] | np.ndarray,
        dt_seconds: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return the componentwise command box enforced by ``project_power``.

        The R272 projection is separable across devices for a fixed previous
        command, SOC, voltage, and time step.  Projecting sufficiently large
        signed requests therefore exposes its exact lower and upper command
        bounds without duplicating the ramp, capability, SOC, and energy rules.
        """

        previous = np.asarray(previous_power_system_pu, dtype=float)
        if previous.shape != (self.device_count,) or not np.all(np.isfinite(previous)):
            raise ValueError("previous power must be a finite device vector")
        probe_magnitude = float(
            4.0
            * (
                1.0
                + np.max(np.abs(previous))
                + self.device_power_limit_system_pu
                + self.device_ramp_limit_system_pu_per_s * dt_seconds
            )
        )
        common = {
            "previous_power_system_pu": previous,
            "soc": soc,
            "voltage_pu": voltage_pu,
            "dt_seconds": dt_seconds,
        }
        lower = self.project_power(
            requested_power_system_pu=np.full(self.device_count, -probe_magnitude),
            **common,
        ).commanded_power_system_pu
        upper = self.project_power(
            requested_power_system_pu=np.full(self.device_count, probe_magnitude),
            **common,
        ).commanded_power_system_pu
        return lower.copy(), upper.copy()

    @property
    def round_trip_efficiency(self) -> float:
        return self.charge_efficiency * self.discharge_efficiency

    def integrate_soc(
        self,
        *,
        actual_power_system_pu: list[float] | np.ndarray,
        soc: list[float] | np.ndarray,
        dt_seconds: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Integrate battery-side energy from signed grid active power."""
        power = np.asarray(actual_power_system_pu, dtype=float)
        current_soc = np.asarray(soc, dtype=float)
        grid_energy_mwh = np.abs(power) * self.system_mva * dt_seconds / 3600.0
        discharged_mwh = np.where(
            power > 0.0,
            grid_energy_mwh / self.discharge_efficiency,
            0.0,
        )
        charged_mwh = np.where(
            power < 0.0,
            grid_energy_mwh * self.charge_efficiency,
            0.0,
        )
        next_soc = current_soc + (charged_mwh - discharged_mwh) / self.device_energy_mwh
        return next_soc, charged_mwh, discharged_mwh

    def project_power(
        self,
        *,
        requested_power_system_pu: list[float] | np.ndarray,
        previous_power_system_pu: list[float] | np.ndarray,
        soc: list[float] | np.ndarray,
        voltage_pu: list[float] | np.ndarray,
        dt_seconds: float,
    ) -> PowerProjection:
        """Apply the shared external ramp to one request vector."""
        requested = np.asarray(requested_power_system_pu, dtype=float)
        previous = np.asarray(previous_power_system_pu, dtype=float)
        current_soc = np.asarray(soc, dtype=float)
        voltage = np.asarray(voltage_pu, dtype=float)
        max_change = self.device_ramp_limit_system_pu_per_s * dt_seconds
        commanded = np.clip(requested, previous - max_change, previous + max_change)
        reasons = [
            ["ramp"] if not np.isclose(command, request) else []
            for command, request in zip(commanded, requested, strict=True)
        ]
        for index, command in enumerate(commanded):
            nameplate_command = float(
                np.clip(
                    command,
                    -self.device_power_limit_system_pu,
                    self.device_power_limit_system_pu,
                )
            )
            if not np.isclose(nameplate_command, command):
                commanded[index] = nameplate_command
                reasons[index].append("power")

            capability_limit = min(
                self.device_power_limit_system_pu,
                max(voltage[index], 0.0)
                * self.active_current_limit_device_pu
                * self.device_power_mva
                / self.system_mva,
            )
            capability_command = float(
                np.clip(commanded[index], -capability_limit, capability_limit)
            )
            if not np.isclose(capability_command, commanded[index]):
                commanded[index] = capability_command
                reasons[index].append("capability")

        for index, command in enumerate(commanded):
            if command > 0.0 and current_soc[index] <= self.soc_min:
                commanded[index] = 0.0
                reasons[index].append("soc_min")
            elif command < 0.0 and current_soc[index] >= self.soc_max:
                commanded[index] = 0.0
                reasons[index].append("soc_max")

        for index, command in enumerate(commanded):
            if command > 0.0:
                energy_limit = (
                    max(current_soc[index] - self.soc_min, 0.0)
                    * self.device_energy_mwh
                    * self.discharge_efficiency
                    * 3600.0
                    / (self.system_mva * dt_seconds)
                )
                if command > energy_limit:
                    commanded[index] = energy_limit
                    reasons[index].append("energy")
            elif command < 0.0:
                energy_limit = (
                    max(self.soc_max - current_soc[index], 0.0)
                    * self.device_energy_mwh
                    / self.charge_efficiency
                    * 3600.0
                    / (self.system_mva * dt_seconds)
                )
                if -command > energy_limit:
                    commanded[index] = -energy_limit
                    reasons[index].append("energy")
        return PowerProjection(
            requested_power_system_pu=requested,
            commanded_power_system_pu=commanded,
            saturation_reasons=tuple(tuple(item) for item in reasons),
        )


def r272_frozen_bess_contract() -> EnergyFeasibleBESSContract:
    """Return the prospectively registered R272 module-aggregate contract."""
    return EnergyFeasibleBESSContract(
        system_mva=100.0,
        device_count=4,
        modules_per_device=50,
        module_power_mva=0.72,
        module_energy_mwh=0.56,
        soc_initial=0.50,
        soc_min=0.20,
        soc_max=0.80,
        charge_efficiency=0.9848857802,
        discharge_efficiency=0.9848857802,
        full_scale_ramp_seconds=1.0,
        active_current_lag_seconds=0.02,
        source_ids=(
            "gerini-2022-doi-10.1016/j.epsr.2022.108567",
            "wecc-esd-modeling-guideline",
            "nerc-2020-fast-frequency-response",
            "andes-2.0.0-esd1-pvd1-dg",
        ),
    )
