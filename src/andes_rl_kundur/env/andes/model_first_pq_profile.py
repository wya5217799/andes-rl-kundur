"""Prospective multi-sample PQ profiles for the model-first ANDES path.

The pure contract stays importable without ANDES.  It emits absolute timed
``PQ.Ppf`` assignments from one immutable baseline and restores that baseline
after the final registered sample.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np

from andes_rl_kundur.env.andes.model_first_pq_disturbance import (
    TimedPQDisturbanceMixin,
    _freeze_constant_power_load,
)

SYSTEM_BASE_MVA = 100.0


@dataclass(frozen=True)
class PQProfileBaseline:
    """One exact PQ baseline row on the system base."""

    device_idx: str
    bus_idx: int
    active_system_pu: float
    reactive_system_pu: float

    def __post_init__(self) -> None:
        if not isinstance(self.device_idx, str) or not self.device_idx:
            raise ValueError("baseline device_idx must be a non-empty string")
        if isinstance(self.bus_idx, bool) or not isinstance(self.bus_idx, int):
            raise ValueError("baseline bus_idx must be an integer")
        values = np.asarray(
            [self.active_system_pu, self.reactive_system_pu], dtype=float
        )
        if not np.all(np.isfinite(values)) or self.active_system_pu < 0.0:
            raise ValueError("baseline PQ values must be finite and active load non-negative")


@dataclass(frozen=True)
class TimedPQProfileContract:
    """One finite active-load profile followed by exact restoration."""

    event_prefix: str
    device_idx: str
    bus_idx: int
    initial_active_system_pu: float
    initial_reactive_system_pu: float
    delta_profile_system_pu: tuple[float, ...]
    plant_baselines: tuple[PQProfileBaseline, ...] = ()
    apply_time_seconds: float = 0.5
    sample_period_seconds: float = 0.2
    system_base_mva: float = SYSTEM_BASE_MVA

    def __post_init__(self) -> None:
        if not isinstance(self.event_prefix, str) or not self.event_prefix:
            raise ValueError("event_prefix must be a non-empty string")
        if not isinstance(self.device_idx, str) or not self.device_idx:
            raise ValueError("device_idx must be a non-empty string")
        if isinstance(self.bus_idx, bool) or not isinstance(self.bus_idx, int):
            raise ValueError("bus_idx must be an integer")
        profile = np.asarray(self.delta_profile_system_pu, dtype=float)
        scalars = np.asarray(
            [
                self.initial_active_system_pu,
                self.initial_reactive_system_pu,
                self.apply_time_seconds,
                self.sample_period_seconds,
                self.system_base_mva,
            ],
            dtype=float,
        )
        if profile.ndim != 1 or profile.size < 1 or not np.all(np.isfinite(profile)):
            raise ValueError("delta_profile_system_pu must be a non-empty finite vector")
        if not np.all(np.isfinite(scalars)):
            raise ValueError("PQ profile baseline, timing, and base must be finite")
        if self.initial_active_system_pu < 0.0:
            raise ValueError("initial active load must be non-negative")
        if np.min(self.initial_active_system_pu + profile) < 0.0:
            raise ValueError("negative load during the profile is forbidden")
        if self.apply_time_seconds < 0.0 or self.sample_period_seconds <= 0.0:
            raise ValueError("profile timing must be positive and ordered")
        if self.system_base_mva <= 0.0:
            raise ValueError("system base must be positive")
        if self.plant_baselines:
            identities = [row.device_idx for row in self.plant_baselines]
            if len(identities) != len(set(identities)):
                raise ValueError("plant baseline device identities must be unique")
            matches = [
                row
                for row in self.plant_baselines
                if row.device_idx == self.device_idx
            ]
            if len(matches) != 1 or matches[0].bus_idx != self.bus_idx:
                raise ValueError("target device must occur once at its registered bus")
            target = matches[0]
            if not np.isclose(
                target.active_system_pu,
                self.initial_active_system_pu,
                rtol=0.0,
                atol=0.0,
            ) or not np.isclose(
                target.reactive_system_pu,
                self.initial_reactive_system_pu,
                rtol=0.0,
                atol=0.0,
            ):
                raise ValueError("target initial PQ values must match its plant baseline")

    @property
    def restore_time_seconds(self) -> float:
        """Return the first sample boundary after the registered profile."""

        return self.apply_time_seconds + (
            len(self.delta_profile_system_pu) * self.sample_period_seconds
        )

    def alter_records(self) -> tuple[dict[str, object], ...]:
        """Return deterministic absolute active-power timed assignments."""

        records = [
            {
                "idx": f"{self.event_prefix}_p_{position}",
                "model": "PQ",
                "dev": self.device_idx,
                "src": "Ppf",
                "t": self.apply_time_seconds
                + position * self.sample_period_seconds,
                "method": "=",
                "amount": self.initial_active_system_pu + float(delta),
            }
            for position, delta in enumerate(self.delta_profile_system_pu)
        ]
        records.append(
            {
                "idx": f"{self.event_prefix}_restore_p",
                "model": "PQ",
                "dev": self.device_idx,
                "src": "Ppf",
                "t": self.restore_time_seconds,
                "method": "=",
                "amount": self.initial_active_system_pu,
            }
        )
        return tuple(records)

    def to_dict(self) -> dict[str, object]:
        """Return the prospective contract as JSON-compatible data."""

        payload = asdict(self)
        payload["delta_profile_system_pu"] = list(self.delta_profile_system_pu)
        payload["restore_time_seconds"] = self.restore_time_seconds
        payload["alter_records"] = list(self.alter_records())
        payload["quantity"] = "active-power consumption"
        payload["positive_sign"] = "increased consumption"
        payload["event_row_semantics"] = "exact-event row is pre-event"
        return payload


class TimedPQProfileMixin(TimedPQDisturbanceMixin):
    """Apply one common PQ baseline before installing a timed profile."""

    pq_profile_contract: TimedPQProfileContract

    @property
    def pq_disturbance_contract(self) -> TimedPQProfileContract:
        """Expose the profile through the audited single-device mixin seam."""

        return self.pq_profile_contract

    def _pre_setup_addons(self, system) -> None:
        super()._pre_setup_addons(system)
        contract = self.pq_profile_contract
        if not contract.plant_baselines:
            raise RuntimeError("the physical profile requires a declared plant baseline")
        indices = [str(value) for value in system.PQ.idx.v]
        for baseline in contract.plant_baselines:
            if indices.count(baseline.device_idx) != 1:
                raise RuntimeError("a registered baseline PQ device is missing or non-unique")
            position = indices.index(baseline.device_idx)
            if int(system.PQ.bus.v[position]) != baseline.bus_idx:
                raise RuntimeError("a registered baseline PQ device moved to another bus")
            system.PQ.set(
                "p0",
                baseline.device_idx,
                float(baseline.active_system_pu),
                attr="v",
            )
            system.PQ.set(
                "q0",
                baseline.device_idx,
                float(baseline.reactive_system_pu),
                attr="v",
            )
        _freeze_constant_power_load(system)
