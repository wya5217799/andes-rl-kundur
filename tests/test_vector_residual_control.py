from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from andes_rl_kundur.control.vector_inertia_residual import (
    execute_edge_residual_numpy,
    r292_vector_residual_contract,
)
from andes_rl_kundur.env.andes.distributed_residual_env import (
    DistributedVectorResidualEnv,
)


class _FakeStorageEnv:
    N_AGENTS = 4
    VSG_SN = 200.0
    DT = 0.2
    STEPS_PER_EPISODE = 4
    andes_nominal_frequency_hz = 60.0

    def __init__(self) -> None:
        self._omega = np.ones(4, dtype=float)
        self._power = np.asarray([0.7, 0.8, 0.9, 1.0], dtype=float)
        self._steps = 0
        self._last_projection = None
        self.last_md_actions: dict[int, np.ndarray] | None = None
        self._vsg_pos = list(range(4))
        self.ss = SimpleNamespace(
            GENCLS=SimpleNamespace(
                M=SimpleNamespace(v=np.full(4, 400.0, dtype=float)),
                D=SimpleNamespace(v=np.full(4, 200.0, dtype=float)),
            )
        )

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
        pass

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
        del bess_power_request_pu
        self.last_md_actions = {
            index: np.asarray(action, dtype=np.float32).copy()
            for index, action in actions.items()
        }
        self._steps += 1
        self._omega += np.asarray([0.0005, 0.0004, -0.0003, -0.0002])
        action_array = np.stack(
            [self.last_md_actions[index] for index in range(4)]
        )
        # R478 corrected convention: runtime arrays are system-base (2x the
        # device-base commands); telemetry stays device-base.
        device_m = 200.0 + 600.0 * action_array[:, 0]
        device_d = 100.0 + 600.0 * action_array[:, 1]
        self.ss.GENCLS.M.v[:] = 2.0 * device_m
        self.ss.GENCLS.D.v[:] = 2.0 * device_d
        info = {
            "freq_hz_physical": self.get_vsg_frequency_physical_hz(),
            "omega_dot": self._compute_omega_dot(self._omega, self._power),
            "andes_nominal_frequency_hz": 60.0,
            "P_es": self._power.copy(),
            "M_es": device_m.copy(),
            "D_es": device_d.copy(),
        }
        return {}, {}, self._steps >= self.STEPS_PER_EPISODE, info


def test_edge_actions_execute_as_bounded_exact_zero_sum_node_residual() -> None:
    contract = r292_vector_residual_contract()

    edge, node, actions = execute_edge_residual_numpy(
        np.asarray([1.0, -1.0, 1.0], dtype=np.float32),
        previous_edge=np.zeros(3, dtype=np.float32),
        step=0,
        contract=contract,
    )

    np.testing.assert_allclose(edge, [0.125, -0.125, 0.125], atol=0.0)
    np.testing.assert_allclose(node, [-0.125, 0.25, -0.25, 0.125], atol=0.0)
    assert float(np.sum(node, dtype=np.float64)) == 0.0
    assert float(np.max(np.abs(node))) <= contract.node_residual_max
    np.testing.assert_allclose(actions[:, 0], 0.25 + node, atol=0.0)
    np.testing.assert_array_equal(actions[:, 1], np.zeros(4, dtype=np.float32))


def test_distributed_environment_exposes_local_obs_and_executes_node_actions() -> None:
    base = _FakeStorageEnv()
    env = DistributedVectorResidualEnv(base)

    observations = env.reset(delta_u={"demo": 1.0})
    assert set(observations) == {0, 1, 2, 3}
    assert all(value.shape == (5,) for value in observations.values())
    np.testing.assert_array_equal(
        [observations[index][4] for index in range(4)],
        [1.0, 1.0, -1.0, -1.0],
    )

    _next_obs, rewards, _done, info = env.step(
        np.asarray([1.0, -1.0, 1.0], dtype=np.float32)
    )

    np.testing.assert_allclose(
        info["r292_node_residual_norm"],
        [-0.125, 0.25, -0.25, 0.125],
        atol=0.0,
    )
    assert info["r292_contract"]["central_action_aggregation"] is False
    assert "r292_q" not in info
    assert sum(rewards.values()) == pytest.approx(info["r292_team_reward"])
    assert base.last_md_actions is not None
    np.testing.assert_allclose(
        np.stack([base.last_md_actions[index] for index in range(4)])[:, 0],
        [0.125, 0.5, 0.0, 0.375],
        atol=0.0,
    )
    np.testing.assert_allclose(
        info["vsg_common_m_model_units"],
        [350.0, 350.0, 350.0, 350.0],
        atol=0.0,
    )
    np.testing.assert_allclose(
        info["vsg_requested_m_model_units"],
        [275.0, 500.0, 200.0, 425.0],
        atol=0.0,
    )
    np.testing.assert_allclose(
        info["vsg_commanded_m_model_units"],
        [275.0, 500.0, 200.0, 425.0],
        atol=0.0,
    )
    np.testing.assert_allclose(
        info["vsg_actual_m_model_units"],
        [275.0, 500.0, 200.0, 425.0],
        atol=0.0,
    )
    np.testing.assert_allclose(
        info["vsg_actual_d_model_units"],
        [100.0, 100.0, 100.0, 100.0],
        atol=0.0,
    )
