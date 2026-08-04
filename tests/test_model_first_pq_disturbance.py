from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from andes_rl_kundur.env.andes.model_first_pq_disturbance import (
    TimedPQDisturbanceContract,
    TimedPQDisturbanceMixin,
    pq_runtime_snapshot,
)


def _contract(delta: float = 0.05) -> TimedPQDisturbanceContract:
    return TimedPQDisturbanceContract(
        device_idx="PQ_Bus14",
        bus_idx=14,
        initial_active_system_pu=2.48,
        initial_reactive_system_pu=0.0,
        delta_active_system_pu=delta,
    )


def test_contract_builds_four_absolute_timed_alter_records() -> None:
    contract = _contract()

    assert contract.alter_records() == (
        {
            "idx": "R333_apply_p",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Ppf",
            "t": 0.5,
            "method": "=",
            "amount": 2.53,
        },
        {
            "idx": "R333_apply_q",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Qpf",
            "t": 0.5,
            "method": "=",
            "amount": 0.0,
        },
        {
            "idx": "R333_restore_p",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Ppf",
            "t": 1.5,
            "method": "=",
            "amount": 2.48,
        },
        {
            "idx": "R333_restore_q",
            "model": "PQ",
            "dev": "PQ_Bus14",
            "src": "Qpf",
            "t": 1.5,
            "method": "=",
            "amount": 0.0,
        },
    )
    assert contract.to_dict()["event_row_semantics"] == "exact-event row is pre-event"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"device_idx": ""},
        {"initial_active_system_pu": 0.0},
        {"delta_active_system_pu": -3.0},
        {"apply_time_seconds": np.nan},
        {"restore_time_seconds": 0.5},
        {"system_base_mva": 0.0},
    ],
)
def test_contract_rejects_ambiguous_event_definitions(kwargs: dict[str, object]) -> None:
    values: dict[str, object] = {
        "device_idx": "PQ_Bus14",
        "bus_idx": 14,
        "initial_active_system_pu": 2.48,
        "initial_reactive_system_pu": 0.0,
        "delta_active_system_pu": 0.05,
    }
    values.update(kwargs)

    with pytest.raises(ValueError):
        TimedPQDisturbanceContract(**values)


class _BaseEnvironment:
    def _pre_setup_addons(self, system) -> None:
        system.base_addons_called = True

    def _build_system(self):
        return self.system


class _EventEnvironment(TimedPQDisturbanceMixin, _BaseEnvironment):
    def __init__(self, system) -> None:
        self.system = system
        self.pq_disturbance_contract = _contract()


def _system():
    pq = SimpleNamespace(
        idx=SimpleNamespace(v=["PQ_Bus14"]),
        bus=SimpleNamespace(v=[14]),
        u=SimpleNamespace(v=[1.0]),
        ue=SimpleNamespace(v=[1.0]),
        Ppf=SimpleNamespace(v=[2.53]),
        Qpf=SimpleNamespace(v=[0.0]),
        vcmp=SimpleNamespace(enable=1),
        config=SimpleNamespace(
            pq2z=1,
            p2p=0.0,
            p2i=0.5,
            p2z=0.5,
            q2q=0.0,
            q2i=0.5,
            q2z=0.5,
        ),
    )
    pq.idx2uid = lambda idx: pq.idx.v.index(idx)
    empty_replacement = SimpleNamespace(
        idx=SimpleNamespace(v=[]),
        pq=SimpleNamespace(v=[]),
        u=SimpleNamespace(v=[]),
        ue=SimpleNamespace(v=[]),
    )
    system = SimpleNamespace(
        PQ=pq,
        FLoad=empty_replacement,
        ZIP=empty_replacement,
        dae=SimpleNamespace(t=0.0),
        Alter=SimpleNamespace(
            idx=SimpleNamespace(v=[row["idx"] for row in _contract().alter_records()]),
            u=SimpleNamespace(v=[1.0, 1.0, 1.0, 1.0]),
            t=SimpleNamespace(callback=lambda is_time: bool(any(is_time))),
        ),
    )
    system.events = []
    system.add = lambda model, payload: system.events.append((model, payload))
    return system


def test_mixin_adds_events_before_setup_and_freezes_constant_power_weights() -> None:
    system = _system()
    env = _EventEnvironment(system)

    env._pre_setup_addons(system)
    built = env._build_system()

    assert system.base_addons_called is True
    assert system.events == [("Alter", row) for row in _contract().alter_records()]
    assert built.PQ.config.p2p == 1.0
    assert built.PQ.config.p2i == 0.0
    assert built.PQ.config.p2z == 0.0
    assert built.PQ.config.q2q == 1.0
    assert built.PQ.config.q2i == 0.0
    assert built.PQ.config.q2z == 0.0
    assert built.PQ.config.pq2z == 0
    assert built.PQ.vcmp.enable == 0
    assert env.pq_setup_snapshot["dae_time_seconds"] == 0.0

    built.Alter.t.callback([True, True, False, False])
    assert env.pq_event_audit[0]["event_ids"] == ["R333_apply_p", "R333_apply_q"]
    assert env.pq_event_audit[0]["callback_action"] is True


def test_runtime_snapshot_detects_live_value_weights_and_replacements() -> None:
    system = _system()
    system.PQ.u.v[0] = 1.0
    system.PQ.ue.v[0] = 0.0
    system.FLoad = SimpleNamespace(
        idx=SimpleNamespace(v=["FL_target", "FL_other"]),
        pq=SimpleNamespace(v=["PQ_Bus14", "PQ_other_at_bus14"]),
        u=SimpleNamespace(v=[1.0, 1.0]),
        ue=SimpleNamespace(v=[1.0, 1.0]),
    )
    system.ZIP = SimpleNamespace(
        idx=SimpleNamespace(v=["ZIP_disabled"]),
        pq=SimpleNamespace(v=["PQ_Bus14"]),
        u=SimpleNamespace(v=[0.0]),
        ue=SimpleNamespace(v=[0.0]),
    )
    _EventEnvironment(system)._build_system()

    snapshot = pq_runtime_snapshot(system, _contract())

    assert snapshot["Ppf_system_pu"] == pytest.approx(2.53)
    assert snapshot["Qpf_system_pu"] == pytest.approx(0.0)
    assert snapshot["raw_active"] is True
    assert snapshot["effective_active"] is False
    assert snapshot["active"] is False
    assert snapshot["active_fload_replacements_for_device"] == 1
    assert snapshot["active_zip_replacements_for_device"] == 0
    assert snapshot["replacement_records"]["FLoad"] == [
        {
            "idx": "FL_target",
            "pq_idx": "PQ_Bus14",
            "raw_active": True,
            "effective_active": True,
        }
    ]
    assert snapshot["replacement_records"]["ZIP"] == [
        {
            "idx": "ZIP_disabled",
            "pq_idx": "PQ_Bus14",
            "raw_active": False,
            "effective_active": False,
        }
    ]
    assert snapshot["pq2z_config"] == 0
    assert snapshot["vcmp_enable"] == 0
    assert snapshot["dae_time_seconds"] == 0.0
    assert snapshot["constant_power_weights"] == {
        "p2p": 1.0,
        "p2i": 0.0,
        "p2z": 0.0,
        "q2q": 1.0,
        "q2i": 0.0,
        "q2z": 0.0,
    }
