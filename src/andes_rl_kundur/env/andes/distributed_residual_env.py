"""R292 local-observation environment for distributed vector execution.

The wrapper preserves the validated slow droop--PI storage controller and the
fixed common-inertia pulse.  Learned control is expressed by three neighbour
edge flows whose incident sums are executed independently at the four VSGs.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import DroopPIActivePowerController
from andes_rl_kundur.control.vector_inertia_residual import (
    INCIDENCE,
    VectorInertiaResidualContract,
    execute_edge_residual_numpy,
    r292_vector_residual_contract,
)
from andes_rl_kundur.evaluation.active_power_authority import (
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
)


class DistributedVectorResidualEnv:
    """Execute neighbour-edge actions from strictly local plant observations."""

    N_AGENTS = 4
    OBS_DIM = 5
    AREA_SIGN = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)

    def __init__(
        self,
        base_env: Any | None = None,
        *,
        contract: VectorInertiaResidualContract | None = None,
    ) -> None:
        if base_env is None:
            from andes_rl_kundur.env.andes.andes_vsg_storage_env import (
                AndesMultiVSGEnvV4Storage,
            )

            base_env = AndesMultiVSGEnvV4Storage(
                random_disturbance=False,
                comm_fail_prob=0.0,
            )
        if int(base_env.N_AGENTS) != self.N_AGENTS:
            raise ValueError("R292 wrapper requires exactly four base agents")
        self.base_env = base_env
        self.contract = contract or r292_vector_residual_contract()
        self.DT = float(base_env.DT)
        self._step_index = 0
        self._previous_edge = np.zeros(self.contract.edge_count, dtype=np.float32)
        self._previous_residual = np.zeros(self.N_AGENTS, dtype=np.float32)
        self._reset_power = np.zeros(self.N_AGENTS, dtype=np.float64)
        self._controller: DroopPIActivePowerController | None = None

    @property
    def STEPS_PER_EPISODE(self) -> int:
        return int(self.base_env.STEPS_PER_EPISODE)

    @STEPS_PER_EPISODE.setter
    def STEPS_PER_EPISODE(self, value: int) -> None:
        self.base_env.STEPS_PER_EPISODE = int(value)

    @property
    def previous_edge(self) -> np.ndarray:
        return self._previous_edge.copy()

    def seed(self, seed: int) -> None:
        self.base_env.seed(seed)

    def close(self) -> None:
        self.base_env.close()

    def _live_physical_state(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        omega = np.asarray(self.base_env._get_vsg_omega(), dtype=np.float64)
        power = np.asarray(self.base_env._get_vsg_power(), dtype=np.float64)
        omega_dot = np.asarray(
            self.base_env._compute_omega_dot(omega, power),
            dtype=np.float64,
        )
        nominal = float(self.base_env.andes_nominal_frequency_hz)
        return omega * nominal, omega_dot * nominal, power

    def _read_actual_vsg_md(self) -> tuple[np.ndarray, np.ndarray]:
        """Read executed M/D directly from the ANDES GENCLS model arrays."""
        positions = tuple(int(value) for value in self.base_env._vsg_pos)
        gencls = self.base_env.ss.GENCLS
        actual_m = np.asarray(
            [gencls.M.v[position] for position in positions],
            dtype=np.float64,
        )
        actual_d = np.asarray(
            [gencls.D.v[position] for position in positions],
            dtype=np.float64,
        )
        if actual_m.shape != (self.N_AGENTS,) or actual_d.shape != (self.N_AGENTS,):
            raise RuntimeError("VSG M/D readback must contain exactly four devices")
        if not np.all(np.isfinite(actual_m)) or not np.all(np.isfinite(actual_d)):
            raise RuntimeError("VSG M/D readback must be finite")
        return actual_m, actual_d

    def _observation(
        self,
        *,
        frequency_hz: np.ndarray,
        rocof_hz_s: np.ndarray,
        power_pu: np.ndarray,
    ) -> dict[int, np.ndarray]:
        nominal = float(self.base_env.andes_nominal_frequency_hz)
        delta_f = np.asarray(frequency_hz, dtype=np.float64) - nominal
        power_delta = np.asarray(power_pu, dtype=np.float64) - self._reset_power
        return {
            index: np.clip(
                np.asarray(
                    [
                        delta_f[index] / 0.1,
                        float(rocof_hz_s[index]) / 0.5,
                        float(self._previous_residual[index])
                        / self.contract.node_residual_max,
                        float(power_delta[index]) / 0.1,
                        float(self.AREA_SIGN[index]),
                    ],
                    dtype=np.float32,
                ),
                -5.0,
                5.0,
            ).astype(np.float32)
            for index in range(self.N_AGENTS)
        }

    def reset(self, *args: Any, **kwargs: Any) -> dict[int, np.ndarray]:
        self.base_env.reset(*args, **kwargs)
        self._step_index = 0
        self._previous_edge = np.zeros(self.contract.edge_count, dtype=np.float32)
        self._previous_residual = np.zeros(self.N_AGENTS, dtype=np.float32)
        frequency, rocof, power = self._live_physical_state()
        self._reset_power = power.copy()
        self._controller = DroopPIActivePowerController(
            device_count=self.N_AGENTS,
            nominal_frequency_hz=float(self.base_env.andes_nominal_frequency_hz),
            kp_system_pu_per_hz_per_device=(
                R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE
            ),
            ki_system_pu_per_hz_s_per_device=(
                R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE
            ),
        )
        return self._observation(
            frequency_hz=frequency,
            rocof_hz_s=rocof,
            power_pu=power,
        )

    def step(
        self,
        raw_edge_actions: np.ndarray,
    ) -> tuple[dict[int, np.ndarray], dict[int, float], bool, dict[str, Any]]:
        if self._controller is None:
            raise RuntimeError("reset must be called before step")
        frequency_before = np.asarray(
            self.base_env.get_vsg_frequency_physical_hz(),
            dtype=np.float64,
        )
        requested_power = self._controller.act(
            frequencies_hz=frequency_before,
            dt_seconds=self.DT,
            previous_projection=self.base_env.last_bess_projection,
        )
        previous_edge = self._previous_edge.copy()
        edge, residual, action_array = execute_edge_residual_numpy(
            raw_edge_actions,
            previous_edge=previous_edge,
            step=self._step_index,
            contract=self.contract,
        )
        md_actions = {
            index: action_array[index].copy()
            for index in range(self.N_AGENTS)
        }
        _legacy_obs, _legacy_rewards, done, info = self.base_env.step(
            md_actions,
            bess_power_request_pu=requested_power,
        )

        frequency = np.asarray(info["freq_hz_physical"], dtype=np.float64)
        rocof = (
            np.asarray(info["omega_dot"], dtype=np.float64)
            * float(info["andes_nominal_frequency_hz"])
        )
        power = np.asarray(info["P_es"], dtype=np.float64)
        nominal = float(info["andes_nominal_frequency_hz"])
        delta_f = frequency - nominal
        common_delta_f = float(np.mean(delta_f))
        differential = delta_f - common_delta_f
        area_difference = float(np.mean(frequency[:2]) - np.mean(frequency[2:]))
        sync_hz2 = float(np.mean(np.square(differential)))
        edge_delta = edge - previous_edge
        reward_terms = {
            "sync": 0.5 * sync_hz2 / (self.contract.sync_scale_hz**2),
            "area": 0.5
            * area_difference**2
            / (self.contract.area_scale_hz**2),
            "action_tv": self.contract.action_tv_weight
            * float(
                np.mean(np.square(edge_delta / self.contract.edge_flow_max))
            ),
        }
        team_reward = -float(sum(reward_terms.values()))

        self._previous_edge = edge.copy()
        self._previous_residual = residual.copy()
        next_obs = self._observation(
            frequency_hz=frequency,
            rocof_hz_s=rocof,
            power_pu=power,
        )
        active = self._step_index < self.contract.active_steps
        common_action = self.contract.common_amplitude if active else 0.0
        expected_common_m = (
            self.contract.baseline_m + self.contract.dm_max * common_action
        )
        common_m = np.full(self.N_AGENTS, expected_common_m, dtype=np.float64)
        raw_edge = np.asarray(raw_edge_actions, dtype=np.float32).reshape(
            self.contract.edge_count
        )
        requested_edge = np.asarray(
            raw_edge * np.float32(self.contract.edge_flow_max),
            dtype=np.float32,
        )
        requested_node = np.asarray(INCIDENCE @ requested_edge, dtype=np.float32)
        requested_m = common_m + self.contract.dm_max * requested_node.astype(np.float64)
        commanded_m = (
            self.contract.baseline_m
            + self.contract.dm_max * action_array[:, 0].astype(np.float64)
        )
        actual_m, actual_d = self._read_actual_vsg_md()
        physical_residual = actual_m - expected_common_m
        info.update(
            {
                "r292_raw_edge_action": raw_edge.copy(),
                "r292_edge_flow_norm": edge.copy(),
                "r292_node_residual_norm": residual.copy(),
                "r292_executed_md_action_norm": action_array.copy(),
                "r292_active": active,
                "r292_physical_m_residual": physical_residual,
                "r292_physical_m_residual_sum": float(
                    np.sum(physical_residual)
                ),
                "r292_incidence_residual_sum": float(
                    np.sum(INCIDENCE @ edge, dtype=np.float64)
                ),
                "r292_sync_hz2_step": sync_hz2,
                "r292_area_difference_hz": area_difference,
                "r292_reward_terms": reward_terms,
                "r292_team_reward": team_reward,
                "r292_contract": self.contract.telemetry(),
                "vsg_common_m_model_units": common_m,
                "vsg_requested_m_model_units": requested_m,
                "vsg_commanded_m_model_units": commanded_m,
                "vsg_actual_m_model_units": actual_m,
                "vsg_actual_d_model_units": actual_d,
            }
        )
        self._step_index += 1
        per_agent_reward = team_reward / self.N_AGENTS
        rewards = {index: per_agent_reward for index in range(self.N_AGENTS)}
        return next_obs, rewards, done, info
