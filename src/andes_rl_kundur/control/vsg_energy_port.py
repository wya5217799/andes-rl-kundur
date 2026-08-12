"""Energy-constrained sampled active-power ports owned by VSG actors.

The public contract keeps three quantities distinct: requested active power,
the projected power command, and the ``GENCLS`` fallback ``pref`` write.  With
no governor, ANDES routes ``pref`` to the mechanical-torque setpoint ``tm0``;
therefore a sampled power command is converted to torque by the sampled speed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.control.active_power import EnergyFeasibleBESSContract


@dataclass(frozen=True)
class VSGEnergyPortDispatch:
    """Auditable output of one sampled per-VSG dispatch decision."""

    requested_power_system_pu: np.ndarray
    commanded_power_system_pu: np.ndarray
    sampled_omega_pu: np.ndarray
    baseline_pref_system_pu: np.ndarray
    pref_system_pu: np.ndarray
    instantaneous_power_at_sample_system_pu: np.ndarray
    saturation_reasons: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class VSGEnergyPortSettlement:
    """Energy settlement derived from achieved port torque and speed."""

    achieved_power_system_pu: np.ndarray
    next_soc: np.ndarray
    charged_energy_mwh: np.ndarray
    discharged_energy_mwh: np.ndarray


class VSGEnergyPortContract:
    """Map bounded per-VSG power requests to sampled ANDES ``pref`` writes."""

    def __init__(self, energy_contract: EnergyFeasibleBESSContract) -> None:
        self.energy_contract = energy_contract

    def dispatch(
        self,
        *,
        requested_power_system_pu: np.ndarray,
        previous_power_system_pu: np.ndarray,
        soc: np.ndarray,
        voltage_pu: np.ndarray,
        sampled_omega_pu: np.ndarray,
        baseline_pref_system_pu: np.ndarray,
        dt_seconds: float,
    ) -> VSGEnergyPortDispatch:
        requested = self._device_vector(
            requested_power_system_pu,
            "requested power",
        )
        previous = self._device_vector(
            previous_power_system_pu,
            "previous power",
        )
        current_soc = self._soc_vector(soc)
        voltage = self._device_vector(voltage_pu, "voltage")
        if np.any(voltage < 0.0):
            raise ValueError("voltage must be a finite nonnegative device vector")
        dt = self._positive_dt(dt_seconds)
        omega = self._device_vector(sampled_omega_pu, "sampled omega")
        if np.any(omega <= 0.0):
            raise ValueError(
                "sampled omega must be a finite positive device vector"
            )
        baseline = self._device_vector(
            baseline_pref_system_pu,
            "baseline pref",
        )
        projection = self.energy_contract.project_power(
            requested_power_system_pu=requested,
            previous_power_system_pu=previous,
            soc=current_soc,
            voltage_pu=voltage,
            dt_seconds=dt,
        )
        torque_residual = projection.commanded_power_system_pu / omega
        pref = baseline + torque_residual
        return VSGEnergyPortDispatch(
            requested_power_system_pu=requested.copy(),
            commanded_power_system_pu=(
                projection.commanded_power_system_pu.copy()
            ),
            sampled_omega_pu=omega.copy(),
            baseline_pref_system_pu=baseline.copy(),
            pref_system_pu=pref,
            instantaneous_power_at_sample_system_pu=torque_residual * omega,
            saturation_reasons=projection.saturation_reasons,
        )

    def settle(
        self,
        *,
        soc: np.ndarray,
        actual_torque_system_pu: np.ndarray,
        baseline_pref_system_pu: np.ndarray,
        actual_omega_pu: np.ndarray,
        dt_seconds: float,
    ) -> VSGEnergyPortSettlement:
        """Settle the energy state from achieved torque and speed readback."""

        current_soc = self._soc_vector(soc)
        dt = self._positive_dt(dt_seconds)
        actual_torque = self._device_vector(
            actual_torque_system_pu,
            "actual torque",
        )
        baseline = self._device_vector(
            baseline_pref_system_pu,
            "baseline pref",
        )
        omega = self._device_vector(actual_omega_pu, "actual omega")
        if np.any(omega <= 0.0):
            raise ValueError("actual omega must be a finite positive device vector")
        achieved_power = (actual_torque - baseline) * omega
        next_soc, charged, discharged = self.energy_contract.integrate_soc(
            actual_power_system_pu=achieved_power,
            soc=current_soc,
            dt_seconds=dt,
        )
        tolerance = 1.0e-12
        if np.any(next_soc < self.energy_contract.soc_min - tolerance) or np.any(
            next_soc > self.energy_contract.soc_max + tolerance
        ):
            raise ValueError(
                "achieved energy settlement crosses registered SOC bounds"
            )
        return VSGEnergyPortSettlement(
            achieved_power_system_pu=achieved_power,
            next_soc=next_soc,
            charged_energy_mwh=charged,
            discharged_energy_mwh=discharged,
        )

    def _device_vector(self, values: np.ndarray, name: str) -> np.ndarray:
        vector = np.asarray(values, dtype=float)
        expected_shape = (self.energy_contract.device_count,)
        if vector.shape != expected_shape or not np.all(np.isfinite(vector)):
            raise ValueError(f"{name} must be a finite {expected_shape} vector")
        return vector

    def _soc_vector(self, values: np.ndarray) -> np.ndarray:
        soc = self._device_vector(values, "soc")
        if np.any(soc < self.energy_contract.soc_min) or np.any(
            soc > self.energy_contract.soc_max
        ):
            raise ValueError("soc must remain inside the registered bounds")
        return soc

    @staticmethod
    def _positive_dt(value: float) -> float:
        dt = float(value)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        return dt
