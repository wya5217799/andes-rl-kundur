"""R278 training/deployment-identical ICEMS residual environment.

This wrapper composes the already validated R274 slow active-power controller,
the R275 common-inertia pulse and the R278 one-dimensional learned residual.
The wrapped V4+ESD1 plant remains unchanged.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.control.active_power import DroopPIActivePowerController
from andes_rl_kundur.control.area_inertia_residual import (
    AREA_PATTERN,
    AreaInertiaResidualContract,
    executed_md_actions_numpy,
    r278_area_inertia_contract,
)
from andes_rl_kundur.evaluation.active_power_authority import (
    R272_KI_SYSTEM_PU_PER_HZ_S_PER_DEVICE,
    R272_KP_SYSTEM_PU_PER_HZ_PER_DEVICE,
)


class ICEMSResidualEnv:
    """Compose frozen classical layers with one learned two-area coordinate."""

    N_AGENTS = 4
    OBS_DIM = 7

    def __init__(
        self,
        base_env: Any | None = None,
        *,
        contract: AreaInertiaResidualContract | None = None,
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
            raise ValueError("R278 wrapper requires exactly four base agents")
        self.base_env = base_env
        self.contract = contract or r278_area_inertia_contract()
        self.DT = float(base_env.DT)
        self._step_index = 0
        self._previous_q = 0.0
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
    def previous_q(self) -> float:
        return float(self._previous_q)

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

    def _observation(
        self,
        *,
        frequency_hz: np.ndarray,
        rocof_hz_s: np.ndarray,
        power_pu: np.ndarray,
    ) -> dict[int, np.ndarray]:
        nominal = float(self.base_env.andes_nominal_frequency_hz)
        delta_f = np.asarray(frequency_hz, dtype=np.float64) - nominal
        common = float(np.mean(delta_f))
        power_delta = np.asarray(power_pu, dtype=np.float64) - self._reset_power
        obs: dict[int, np.ndarray] = {}
        for index in range(self.N_AGENTS):
            values = np.asarray(
                [
                    delta_f[index] / 0.1,
                    common / 0.1,
                    (delta_f[index] - common) / 0.05,
                    float(rocof_hz_s[index]) / 0.5,
                    float(self._previous_residual[index])
                    / self.contract.q_max,
                    float(power_delta[index]) / 0.1,
                    float(AREA_PATTERN[index]),
                ],
                dtype=np.float32,
            )
            obs[index] = np.clip(values, -5.0, 5.0).astype(np.float32)
        return obs

    def reset(self, *args: Any, **kwargs: Any) -> dict[int, np.ndarray]:
        self.base_env.reset(*args, **kwargs)
        self._step_index = 0
        self._previous_q = 0.0
        self._previous_residual = np.zeros(self.N_AGENTS, dtype=np.float32)
        frequency, rocof, power = self._live_physical_state()
        self._reset_power = power.copy()
        self._controller = DroopPIActivePowerController(
            device_count=self.N_AGENTS,
            nominal_frequency_hz=float(
                self.base_env.andes_nominal_frequency_hz
            ),
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

    @staticmethod
    def _raw_vector(raw_actions: dict[int, Any] | np.ndarray) -> np.ndarray:
        if isinstance(raw_actions, dict):
            if set(raw_actions) != set(range(4)):
                raise ValueError("raw_actions must contain exactly agents 0..3")
            raw = np.asarray(
                [
                    float(np.asarray(raw_actions[index]).reshape(-1)[0])
                    for index in range(4)
                ],
                dtype=np.float32,
            )
        else:
            raw = np.asarray(raw_actions, dtype=np.float32).reshape(-1)
        if raw.shape != (4,):
            raise ValueError(f"raw_actions must have shape (4,), got {raw.shape}")
        if not np.all(np.isfinite(raw)):
            raise ValueError("raw_actions must be finite")
        return np.clip(raw, -1.0, 1.0)

    def step(
        self,
        raw_actions: dict[int, Any] | np.ndarray,
    ) -> tuple[dict[int, np.ndarray], dict[int, float], bool, dict[str, Any]]:
        if self._controller is None:
            raise RuntimeError("reset must be called before step")
        raw = self._raw_vector(raw_actions)
        frequency_before = np.asarray(
            self.base_env.get_vsg_frequency_physical_hz(),
            dtype=np.float64,
        )
        requested_power = self._controller.act(
            frequencies_hz=frequency_before,
            dt_seconds=self.DT,
            previous_projection=self.base_env.last_bess_projection,
        )
        previous_q = self._previous_q
        q, residual, action_array = executed_md_actions_numpy(
            raw,
            previous_q=previous_q,
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
        area_difference = float(
            np.mean(frequency[:2]) - np.mean(frequency[2:])
        )
        sync_hz2 = float(np.mean(np.square(differential)))
        delta_q = float(q - previous_q)
        reward_terms = {
            "sync": 0.5
            * sync_hz2
            / (self.contract.sync_scale_hz**2),
            "area": 0.5
            * area_difference**2
            / (self.contract.area_scale_hz**2),
            "action_tv": self.contract.action_tv_weight
            * (delta_q / self.contract.q_max) ** 2,
        }
        team_reward = -float(sum(reward_terms.values()))

        self._previous_q = q
        self._previous_residual = residual.astype(np.float32)
        next_obs = self._observation(
            frequency_hz=frequency,
            rocof_hz_s=rocof,
            power_pu=power,
        )
        active = self._step_index < self.contract.active_steps
        common_action = self.contract.common_amplitude if active else 0.0
        expected_common_m = (
            self.contract.baseline_m
            + self.contract.dm_max * common_action
        )
        physical_residual = (
            np.asarray(info["M_es"], dtype=np.float64)
            - expected_common_m
        )
        info.update(
            {
                "r278_raw_z": raw.copy(),
                "r278_q": float(q),
                "r278_q_normalized": float(q / self.contract.q_max),
                "r278_residual_action_norm": residual.copy(),
                "r278_executed_md_action_norm": action_array.copy(),
                "r278_active": active,
                "r278_physical_m_residual": physical_residual,
                "r278_physical_m_residual_sum": float(
                    np.sum(physical_residual)
                ),
                "r278_sync_hz2_step": sync_hz2,
                "r278_area_difference_hz": area_difference,
                "r278_reward_terms": reward_terms,
                "r278_team_reward": team_reward,
                "r278_contract": self.contract.telemetry(),
            }
        )
        self._step_index += 1
        per_agent_reward = team_reward / self.N_AGENTS
        rewards = {
            index: per_agent_reward for index in range(self.N_AGENTS)
        }
        return next_obs, rewards, done, info
