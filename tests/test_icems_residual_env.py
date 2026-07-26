from __future__ import annotations

import os

import numpy as np
import pytest

from andes_rl_kundur.env.andes.icems_residual_env import ICEMSResidualEnv


class _FakeStorageEnv:
    N_AGENTS = 4
    DT = 0.2
    STEPS_PER_EPISODE = 4
    FN = 50.0
    andes_nominal_frequency_hz = 60.0

    def __init__(self) -> None:
        self._omega = np.ones(4, dtype=float)
        self._power = np.asarray([0.7, 0.8, 0.9, 1.0], dtype=float)
        self._steps = 0
        self._last_projection = None
        self.last_md_actions: dict[int, np.ndarray] | None = None
        self.last_bess_request: np.ndarray | None = None
        self.closed = False

    @property
    def last_bess_projection(self):
        return self._last_projection

    def seed(self, seed: int) -> None:
        self.seed_value = seed

    def reset(self, *args, **kwargs):
        del args, kwargs
        self._omega[:] = 1.0
        self._steps = 0
        self._last_projection = None
        return {index: np.zeros(7, dtype=np.float32) for index in range(4)}

    def close(self) -> None:
        self.closed = True

    def _get_vsg_omega(self) -> np.ndarray:
        return self._omega.copy()

    def _get_vsg_power(self) -> np.ndarray:
        return self._power.copy()

    def _compute_omega_dot(
        self,
        omega: np.ndarray,
        power: np.ndarray,
    ) -> np.ndarray:
        del power
        return -(omega - 1.0)

    def get_vsg_frequency_physical_hz(self) -> np.ndarray:
        return self._omega * self.andes_nominal_frequency_hz

    def step(self, actions, *, bess_power_request_pu):
        self.last_md_actions = {
            index: np.asarray(action, dtype=np.float32).copy()
            for index, action in actions.items()
        }
        self.last_bess_request = np.asarray(
            bess_power_request_pu,
            dtype=float,
        )
        self._steps += 1
        self._omega += np.asarray(
            [0.0005, 0.0004, -0.0003, -0.0002],
            dtype=float,
        )
        frequency = self.get_vsg_frequency_physical_hz()
        omega_dot = self._compute_omega_dot(self._omega, self._power)
        action_array = np.stack(
            [self.last_md_actions[index] for index in range(4)]
        )
        info = {
            "freq_hz_physical": frequency,
            "omega_dot": omega_dot,
            "andes_nominal_frequency_hz": 60.0,
            "P_es": self._power.copy(),
            "M_es": 200.0 + 600.0 * action_array[:, 0],
            "D_es": 100.0 + 600.0 * action_array[:, 1],
        }
        done = self._steps >= self.STEPS_PER_EPISODE
        return {}, {index: 0.0 for index in range(4)}, done, info


def test_zero_residual_executes_exact_r275_common_action() -> None:
    base = _FakeStorageEnv()
    env = ICEMSResidualEnv(base)
    obs = env.reset(delta_u={"demo": 1.0})
    assert set(obs) == {0, 1, 2, 3}
    assert all(value.shape == (7,) for value in obs.values())

    next_obs, rewards, done, info = env.step(np.zeros(4, dtype=np.float32))
    assert not done
    assert set(next_obs) == set(rewards) == {0, 1, 2, 3}
    assert info["r278_q"] == 0.0
    np.testing.assert_allclose(
        info["r278_executed_md_action_norm"][:, 0],
        np.full(4, 0.25),
    )
    np.testing.assert_array_equal(
        info["r278_executed_md_action_norm"][:, 1],
        np.zeros(4),
    )
    assert info["r278_physical_m_residual_sum"] == pytest.approx(0.0)


def test_two_area_action_preserves_physical_fleet_mean_and_d_zero() -> None:
    base = _FakeStorageEnv()
    env = ICEMSResidualEnv(base)
    env.reset()
    raw = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)
    _obs, _rewards, _done, info = env.step(raw)
    assert info["r278_q"] == pytest.approx(0.25)
    np.testing.assert_allclose(
        info["r278_executed_md_action_norm"][:, 0],
        [0.5, 0.5, 0.0, 0.0],
    )
    np.testing.assert_array_equal(
        info["r278_executed_md_action_norm"][:, 1],
        np.zeros(4),
    )
    assert info["r278_physical_m_residual_sum"] == pytest.approx(0.0)
    assert sum(_rewards.values()) == pytest.approx(
        info["r278_team_reward"]
    )


def test_reset_clears_previous_q_and_observation_residual() -> None:
    env = ICEMSResidualEnv(_FakeStorageEnv())
    env.reset()
    env.step(np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32))
    assert env.previous_q == pytest.approx(0.25)
    obs = env.reset()
    assert env.previous_q == 0.0
    assert all(float(value[4]) == 0.0 for value in obs.values())


@pytest.mark.skipif(
    "microsoft" not in os.uname().release.lower()
    if hasattr(os, "uname")
    else True,
    reason="real ANDES integration runs only in WSL",
)
def test_real_andes_r278_wrapper_produces_exact_one_step_action() -> None:
    env = ICEMSResidualEnv()
    env.seed(42)
    env.STEPS_PER_EPISODE = 1
    try:
        env.reset(delta_u={"PQ_0": 0.5})
        _obs, _rewards, done, info = env.step(np.zeros(4, dtype=np.float32))
    finally:
        env.close()
    assert done
    assert not info["tds_failed"]
    np.testing.assert_allclose(
        info["r278_executed_md_action_norm"][:, 0],
        np.full(4, 0.25),
        rtol=0.0,
        atol=1e-9,
    )
    assert abs(info["r278_physical_m_residual_sum"]) <= 1e-8
