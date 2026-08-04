"""R293 environment adding a fixed RoCoF term to the R292 team objective."""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.env.andes.distributed_residual_env import (
    DistributedVectorResidualEnv,
)

R293_ROCOF_REWARD_WEIGHT = 0.25
R293_ROCOF_SCALE_HZ_S = 0.5


class PriorResidualEnv(DistributedVectorResidualEnv):
    """Preserve R292 physics while penalising the observed RoCoF failure mode."""

    def step(
        self,
        raw_edge_actions: np.ndarray,
    ) -> tuple[dict[int, np.ndarray], dict[int, float], bool, dict[str, Any]]:
        observations, _rewards, done, info = super().step(raw_edge_actions)
        rocof = (
            np.asarray(info["omega_dot"], dtype=np.float64)
            * float(info["andes_nominal_frequency_hz"])
        )
        rocof_penalty = R293_ROCOF_REWARD_WEIGHT * float(
            np.max(np.square(rocof / R293_ROCOF_SCALE_HZ_S))
        )
        reward_terms = dict(info["r292_reward_terms"])
        reward_terms["max_rocof"] = rocof_penalty
        team_reward = -float(sum(reward_terms.values()))
        rewards = {index: team_reward / self.N_AGENTS for index in range(self.N_AGENTS)}
        info.update(
            {
                "r293_reward_terms": reward_terms,
                "r293_team_reward": team_reward,
                "r293_rocof_reward_weight": R293_ROCOF_REWARD_WEIGHT,
                "r293_rocof_scale_hz_s": R293_ROCOF_SCALE_HZ_S,
            }
        )
        return observations, rewards, done, info
