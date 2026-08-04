from __future__ import annotations

import pytest

from andes_rl_kundur.env.andes.model_first_pq_profile import (
    PQProfileBaseline,
    TimedPQProfileContract,
    TimedPQProfileMixin,
)


def test_profile_contract_emits_absolute_samples_and_exact_restore() -> None:
    contract = TimedPQProfileContract(
        event_prefix="R335_PQ_Bus15_triangle_positive",
        device_idx="PQ_Bus15",
        bus_idx=15,
        initial_active_system_pu=0.05,
        initial_reactive_system_pu=0.0,
        delta_profile_system_pu=(0.02, 0.04, 0.05, 0.04, 0.02),
    )

    assert contract.alter_records() == (
        {
            "idx": "R335_PQ_Bus15_triangle_positive_p_0",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 0.5,
            "method": "=",
            "amount": pytest.approx(0.07),
        },
        {
            "idx": "R335_PQ_Bus15_triangle_positive_p_1",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 0.7,
            "method": "=",
            "amount": pytest.approx(0.09),
        },
        {
            "idx": "R335_PQ_Bus15_triangle_positive_p_2",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 0.9,
            "method": "=",
            "amount": pytest.approx(0.10),
        },
        {
            "idx": "R335_PQ_Bus15_triangle_positive_p_3",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 1.1,
            "method": "=",
            "amount": pytest.approx(0.09),
        },
        {
            "idx": "R335_PQ_Bus15_triangle_positive_p_4",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 1.3,
            "method": "=",
            "amount": pytest.approx(0.07),
        },
        {
            "idx": "R335_PQ_Bus15_triangle_positive_restore_p",
            "model": "PQ",
            "dev": "PQ_Bus15",
            "src": "Ppf",
            "t": 1.5,
            "method": "=",
            "amount": pytest.approx(0.05),
        },
    )


class _BaseEnvironment:
    def _pre_setup_addons(self, system) -> None:
        system.base_addons_called = True


class _ProfileEnvironment(TimedPQProfileMixin, _BaseEnvironment):
    def __init__(self, contract: TimedPQProfileContract) -> None:
        self.pq_profile_contract = contract


def test_profile_mixin_applies_one_common_four_load_baseline_before_events() -> None:
    baselines = (
        PQProfileBaseline("PQ_0", 7, 11.59, -0.735),
        PQProfileBaseline("PQ_1", 8, 15.75, -0.899),
        PQProfileBaseline("PQ_Bus14", 14, 2.48, 0.0),
        PQProfileBaseline("PQ_Bus15", 15, 0.05, 0.0),
    )
    contract = TimedPQProfileContract(
        event_prefix="R335_PQ_0_impulse_positive",
        device_idx="PQ_0",
        bus_idx=7,
        initial_active_system_pu=11.59,
        initial_reactive_system_pu=-0.735,
        delta_profile_system_pu=(0.05,),
        plant_baselines=baselines,
    )
    pq = type("PQ", (), {})()
    pq.idx = type("Idx", (), {"v": [row.device_idx for row in baselines]})()
    pq.bus = type("Bus", (), {"v": [row.bus_idx for row in baselines]})()
    pq.p0 = type("P0", (), {"v": [0.0] * 4})()
    pq.q0 = type("Q0", (), {"v": [0.0] * 4})()
    pq.config = type(
        "Config",
        (),
        {
            "pq2z": 1,
            "p2p": 0.0,
            "p2i": 0.5,
            "p2z": 0.5,
            "q2q": 0.0,
            "q2i": 0.5,
            "q2z": 0.5,
        },
    )()
    pq.vcmp = type("VCmp", (), {"enable": 1})()

    def set_value(name: str, idx: str, value: float, *, attr: str) -> None:
        assert attr == "v"
        getattr(pq, name).v[pq.idx.v.index(idx)] = value

    pq.set = set_value
    system = type("System", (), {})()
    system.PQ = pq
    system.events = []
    system.add = lambda model, payload: system.events.append((model, payload))

    _ProfileEnvironment(contract)._pre_setup_addons(system)

    assert system.base_addons_called is True
    assert pq.p0.v == pytest.approx([11.59, 15.75, 2.48, 0.05])
    assert pq.q0.v == pytest.approx([-0.735, -0.899, 0.0, 0.0])
    assert system.events == [("Alter", row) for row in contract.alter_records()]
    assert pq.config.p2p == 1.0
    assert pq.config.p2i == 0.0
    assert pq.config.p2z == 0.0
    assert pq.config.q2q == 1.0
    assert pq.config.q2i == 0.0
    assert pq.config.q2z == 0.0
