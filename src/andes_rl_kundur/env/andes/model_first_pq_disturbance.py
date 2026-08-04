"""Prospective timed PQ events for the model-first ANDES path.

The module stays importable without ANDES.  It defines a validated four-event
contract and a mixin whose pre-setup hook adds absolute ``Alter`` assignments.
The sealed model-first environment remains untouched; a runner composes the
mixin with that environment only inside the WSL execution process.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

SYSTEM_BASE_MVA = 100.0


def _freeze_constant_power_load(system: Any) -> None:
    """Freeze both configuration and the already-constructed limiter switch."""

    config = system.PQ.config
    config.pq2z = 0
    config.p2p = 1.0
    config.p2i = 0.0
    config.p2z = 0.0
    config.q2q = 1.0
    config.q2i = 0.0
    config.q2z = 0.0
    system.PQ.vcmp.enable = 0


@dataclass(frozen=True)
class TimedPQDisturbanceContract:
    """One active-load step and exact restoration through timed Alter events."""

    device_idx: str
    bus_idx: int
    initial_active_system_pu: float
    initial_reactive_system_pu: float
    delta_active_system_pu: float
    apply_time_seconds: float = 0.5
    restore_time_seconds: float = 1.5
    system_base_mva: float = SYSTEM_BASE_MVA

    def __post_init__(self) -> None:
        finite = (
            self.initial_active_system_pu,
            self.initial_reactive_system_pu,
            self.delta_active_system_pu,
            self.apply_time_seconds,
            self.restore_time_seconds,
            self.system_base_mva,
        )
        if not isinstance(self.device_idx, str) or not self.device_idx:
            raise ValueError("device_idx must be a non-empty string")
        if isinstance(self.bus_idx, bool) or not isinstance(self.bus_idx, int):
            raise ValueError("bus_idx must be an integer")
        if not all(np.isfinite(float(value)) for value in finite):
            raise ValueError("PQ event values and times must be finite")
        if self.initial_active_system_pu <= 0.0:
            raise ValueError("initial active load must be positive")
        if self.disturbed_active_system_pu < 0.0:
            raise ValueError("negative load after the event is forbidden")
        if self.apply_time_seconds < 0.0:
            raise ValueError("apply time must be non-negative")
        if self.restore_time_seconds <= self.apply_time_seconds:
            raise ValueError("restore time must be after apply time")
        if self.system_base_mva <= 0.0:
            raise ValueError("system base must be positive")

    @property
    def disturbed_active_system_pu(self) -> float:
        """Return the absolute post-event active load on the system base."""

        return self.initial_active_system_pu + self.delta_active_system_pu

    def alter_records(self) -> tuple[dict[str, object], ...]:
        """Return four deterministic pre-setup ``Alter`` declarations."""

        values = (
            (
                "apply_p",
                self.apply_time_seconds,
                "Ppf",
                self.disturbed_active_system_pu,
            ),
            (
                "apply_q",
                self.apply_time_seconds,
                "Qpf",
                self.initial_reactive_system_pu,
            ),
            (
                "restore_p",
                self.restore_time_seconds,
                "Ppf",
                self.initial_active_system_pu,
            ),
            (
                "restore_q",
                self.restore_time_seconds,
                "Qpf",
                self.initial_reactive_system_pu,
            ),
        )
        return tuple(
            {
                "idx": f"R333_{label}",
                "model": "PQ",
                "dev": self.device_idx,
                "src": source,
                "t": time,
                "method": "=",
                "amount": amount,
            }
            for label, time, source, amount in values
        )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-compatible prospective contract."""

        payload = asdict(self)
        payload["disturbed_active_system_pu"] = self.disturbed_active_system_pu
        payload["alter_records"] = list(self.alter_records())
        payload["quantity"] = "active-power consumption"
        payload["positive_sign"] = "increased consumption"
        payload["event_row_semantics"] = "exact-event row is pre-event"
        return payload


class TimedPQDisturbanceMixin:
    """Compose timed PQ events with an ANDES environment before ``setup()``."""

    pq_disturbance_contract: TimedPQDisturbanceContract

    def _pre_setup_addons(self, system: Any) -> None:
        super()._pre_setup_addons(system)
        contract = self.pq_disturbance_contract
        indices = [str(value) for value in system.PQ.idx.v]
        if indices.count(contract.device_idx) != 1:
            raise RuntimeError("the registered PQ device is missing or non-unique")
        _freeze_constant_power_load(system)
        for event in contract.alter_records():
            system.add("Alter", dict(event))

    def _build_system(self):
        system = super()._build_system()
        _freeze_constant_power_load(system)
        self.pq_setup_snapshot = pq_runtime_snapshot(
            system,
            self.pq_disturbance_contract,
        )
        self.pq_event_audit: list[dict[str, object]] = []
        original_callback = system.Alter.t.callback

        def audited_callback(is_time):
            active_positions = [
                position
                for position, active in enumerate(is_time)
                if bool(active) and float(system.Alter.u.v[position]) == 1.0
            ]
            if not active_positions:
                return original_callback(is_time)
            before = pq_runtime_snapshot(system, self.pq_disturbance_contract)
            action = original_callback(is_time)
            after = pq_runtime_snapshot(system, self.pq_disturbance_contract)
            self.pq_event_audit.append(
                {
                    "dae_time_seconds": float(system.dae.t),
                    "event_ids": [
                        str(system.Alter.idx.v[position])
                        for position in active_positions
                    ],
                    "before": before,
                    "after": after,
                    "callback_action": bool(action),
                }
            )
            return action

        system.Alter.t.callback = audited_callback
        return system


def pq_runtime_snapshot(
    system: Any,
    contract: TimedPQDisturbanceContract,
) -> dict[str, object]:
    """Read the live PQ value, conversion weights, status, and replacements."""

    indices = [str(value) for value in system.PQ.idx.v]
    if indices.count(contract.device_idx) != 1:
        raise RuntimeError("the registered PQ device is missing or non-unique")
    position = int(system.PQ.idx2uid(contract.device_idx))
    bus_values = list(system.PQ.bus.v)
    if int(bus_values[position]) != contract.bus_idx:
        raise RuntimeError("the registered PQ device moved to another bus")

    def replacement_records(model_name: str) -> list[dict[str, object]]:
        model = getattr(system, model_name, None)
        if model is None or not hasattr(model, "pq"):
            return []
        rows: list[dict[str, object]] = []
        for idx, pq_idx, raw, effective in zip(
            model.idx.v,
            model.pq.v,
            model.u.v,
            model.ue.v,
            strict=True,
        ):
            if str(pq_idx) != contract.device_idx:
                continue
            rows.append(
                {
                    "idx": str(idx),
                    "pq_idx": str(pq_idx),
                    "raw_active": bool(float(raw) == 1.0),
                    "effective_active": bool(float(effective) == 1.0),
                }
            )
        return rows

    config = system.PQ.config
    fload_records = replacement_records("FLoad")
    zip_records = replacement_records("ZIP")
    raw_active = bool(float(system.PQ.u.v[position]) == 1.0)
    effective_active = bool(float(system.PQ.ue.v[position]) == 1.0)
    return {
        "device_idx": contract.device_idx,
        "bus_idx": contract.bus_idx,
        "dae_time_seconds": float(system.dae.t),
        "raw_active": raw_active,
        "effective_active": effective_active,
        "active": effective_active,
        "Ppf_system_pu": float(system.PQ.Ppf.v[position]),
        "Qpf_system_pu": float(system.PQ.Qpf.v[position]),
        "pq2z_config": int(config.pq2z),
        "vcmp_enable": int(system.PQ.vcmp.enable),
        "constant_power_weights": {
            "p2p": float(config.p2p),
            "p2i": float(config.p2i),
            "p2z": float(config.p2z),
            "q2q": float(config.q2q),
            "q2i": float(config.q2i),
            "q2z": float(config.q2z),
        },
        "replacement_records": {
            "FLoad": fload_records,
            "ZIP": zip_records,
        },
        "active_fload_replacements_for_device": sum(
            int(row["raw_active"] is True) for row in fload_records
        ),
        "active_zip_replacements_for_device": sum(
            int(row["raw_active"] is True) for row in zip_records
        ),
    }
