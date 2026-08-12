from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.vsg_energy_port import VSGEnergyPortContract
from andes_rl_kundur.env.andes.vsg_energy_port_env import AndesVSGEnergyPortEnv


class _Vector:
    def __init__(self, values: list[float]) -> None:
        self.v = np.asarray(values, dtype=float)


class _FakeSynGen:
    def __init__(self, preferences: dict[str, float]) -> None:
        self.preferences = preferences
        self.writes: list[tuple[str, float]] = []

    def get_pref(self, _system: object, index: str) -> float:
        return self.preferences[index]

    def set_pref(self, _system: object, index: str, value: float) -> None:
        self.preferences[index] = value
        self.writes.append((index, value))


class _FakeSystem:
    def __init__(self) -> None:
        self.SynGen = _FakeSynGen(
            {f"VSG_{index}": 0.5 for index in range(1, 5)}
        )
        self.GENCLS = type(
            "FakeGENCLS",
            (),
            {
                "omega": _Vector([1.0, 1.0, 1.0, 1.0]),
                "v": _Vector([1.0, 1.0, 1.0, 1.0]),
                "tm": _Vector([0.5, 0.5, 0.5, 0.5]),
            },
        )()


class _FakeBaseEnv:
    N_AGENTS = 4
    DT = 0.2

    def __init__(self) -> None:
        self.vsg_idx = [f"VSG_{index}" for index in range(1, 5)]
        self._vsg_pos = [0, 1, 2, 3]
        self.ss = _FakeSystem()
        self.last_actions: dict[int, np.ndarray] | None = None

    def reset(self) -> dict[int, np.ndarray]:
        return {index: np.zeros(3) for index in range(self.N_AGENTS)}

    def step(
        self,
        actions: dict[int, np.ndarray],
    ) -> tuple[dict[int, np.ndarray], dict[int, float], bool, dict[str, object]]:
        self.last_actions = actions
        self.ss.GENCLS.omega.v = np.asarray([1.001, 1.0, 1.0, 1.0])
        self.ss.GENCLS.tm.v = np.asarray([0.535, 0.5, 0.5, 0.5])
        return (
            {index: np.ones(3) for index in range(self.N_AGENTS)},
            {index: 0.0 for index in range(self.N_AGENTS)},
            False,
            {"base": "preserved"},
        )


def test_dispatch_converts_four_power_commands_to_sampled_vsg_pref() -> None:
    contract = VSGEnergyPortContract(r272_frozen_bess_contract())
    requested = np.asarray([0.04, -0.04, 0.02, -0.02])
    omega = np.asarray([1.0, 0.99, 1.01, 1.0])
    baseline_pref = np.full(4, 0.5)

    dispatch = contract.dispatch(
        requested_power_system_pu=requested,
        previous_power_system_pu=np.zeros(4),
        soc=np.full(4, 0.5),
        voltage_pu=np.ones(4),
        sampled_omega_pu=omega,
        baseline_pref_system_pu=baseline_pref,
        dt_seconds=0.2,
    )

    assert np.array_equal(dispatch.commanded_power_system_pu, requested)
    assert np.allclose(dispatch.pref_system_pu, baseline_pref + requested / omega)
    assert np.allclose(
        dispatch.instantaneous_power_at_sample_system_pu,
        requested,
        rtol=0.0,
        atol=1.0e-12,
    )
    assert dispatch.saturation_reasons == ((), (), (), ())


def test_dispatch_rejects_nonpositive_or_misaligned_speed_samples() -> None:
    contract = VSGEnergyPortContract(r272_frozen_bess_contract())
    common = {
        "requested_power_system_pu": np.zeros(4),
        "previous_power_system_pu": np.zeros(4),
        "soc": np.full(4, 0.5),
        "voltage_pu": np.ones(4),
        "baseline_pref_system_pu": np.full(4, 0.5),
        "dt_seconds": 0.2,
    }

    with pytest.raises(ValueError, match="sampled omega"):
        contract.dispatch(sampled_omega_pu=np.asarray([1.0, 1.0, 0.0, 1.0]), **common)
    with pytest.raises(ValueError, match="sampled omega"):
        contract.dispatch(sampled_omega_pu=np.ones(3), **common)


@pytest.mark.parametrize(
    ("field", "invalid", "message"),
    [
        ("requested_power_system_pu", np.zeros(3), "requested power"),
        ("previous_power_system_pu", np.zeros(3), "previous power"),
        ("soc", np.full(3, 0.5), "soc"),
        ("voltage_pu", np.ones(3), "voltage"),
    ],
)
def test_dispatch_rejects_any_actor_vector_that_is_not_four_finite_values(
    field: str,
    invalid: np.ndarray,
    message: str,
) -> None:
    contract = VSGEnergyPortContract(r272_frozen_bess_contract())
    arguments = {
        "requested_power_system_pu": np.zeros(4),
        "previous_power_system_pu": np.zeros(4),
        "soc": np.full(4, 0.5),
        "voltage_pu": np.ones(4),
        "sampled_omega_pu": np.ones(4),
        "baseline_pref_system_pu": np.full(4, 0.5),
        "dt_seconds": 0.2,
    }
    arguments[field] = invalid

    with pytest.raises(ValueError, match=message):
        contract.dispatch(**arguments)


def test_settle_updates_soc_from_achieved_pref_and_speed_not_command() -> None:
    contract = VSGEnergyPortContract(r272_frozen_bess_contract())

    settlement = contract.settle(
        soc=np.full(4, 0.5),
        actual_torque_system_pu=np.asarray([0.6, 0.4, 0.5, 0.55]),
        baseline_pref_system_pu=np.full(4, 0.5),
        actual_omega_pu=np.ones(4),
        dt_seconds=360.0,
    )

    assert np.allclose(
        settlement.achieved_power_system_pu,
        [0.1, -0.1, 0.0, 0.05],
        rtol=0.0,
        atol=1.0e-12,
    )
    assert np.allclose(
        settlement.next_soc,
        [0.4637376369602643, 0.53517449215, 0.5, 0.4818688184801322],
        rtol=0.0,
        atol=1.0e-12,
    )


def test_settle_rejects_achieved_energy_that_crosses_registered_soc_bounds() -> None:
    contract = VSGEnergyPortContract(r272_frozen_bess_contract())

    with pytest.raises(ValueError, match="energy settlement"):
        contract.settle(
            soc=np.full(4, 0.2),
            actual_torque_system_pu=np.asarray([0.6, 0.5, 0.5, 0.5]),
            baseline_pref_system_pu=np.full(4, 0.5),
            actual_omega_pu=np.ones(4),
            dt_seconds=360.0,
        )


def test_env_writes_one_pref_per_vsg_and_forces_legacy_actions_to_zero() -> None:
    base = _FakeBaseEnv()
    env = AndesVSGEnergyPortEnv(base_env=base)

    reset_observation = env.reset()
    observation, rewards, done, info = env.step(np.asarray([0.04, 0.0, 0.0, 0.0]))

    assert set(reset_observation) == {0, 1, 2, 3}
    assert set(observation) == {0, 1, 2, 3}
    assert rewards == {0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
    assert done is False
    assert base.ss.SynGen.writes == [
        ("VSG_1", 0.54),
        ("VSG_2", 0.5),
        ("VSG_3", 0.5),
        ("VSG_4", 0.5),
    ]
    assert base.last_actions is not None
    assert all(
        np.array_equal(base.last_actions[index], np.zeros(2))
        for index in range(4)
    )
    assert info["base"] == "preserved"
    assert np.allclose(
        info["vsg_energy_port_pref_readback_system_pu"],
        [0.54, 0.5, 0.5, 0.5],
        rtol=0.0,
        atol=1.0e-12,
    )
    assert np.allclose(
        info["vsg_energy_port_sampled_omega_pu"],
        [1.0, 1.0, 1.0, 1.0],
        rtol=0.0,
        atol=1.0e-12,
    )
    assert np.allclose(
        info["vsg_energy_port_torque_readback_system_pu"],
        [0.535, 0.5, 0.5, 0.5],
        rtol=0.0,
        atol=1.0e-12,
    )
    assert np.allclose(
        info["vsg_energy_port_achieved_power_system_pu"],
        [0.0350175, 0.0, 0.0, 0.0],
        rtol=0.0,
        atol=1.0e-12,
    )
    assert info["vsg_energy_port_object_semantics"] == (
        "VSG-owned sampled pref/tm0 port; no ESD1"
    )
