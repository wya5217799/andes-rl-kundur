"""R293 centralized and neighbour-only TD3 residuals over a classical prior."""

from __future__ import annotations

import numpy as np
import torch
from torch import nn

from andes_rl_kundur.agents.vector_residual_td3 import (
    CentralVectorTD3,
    DistributedEdgeTD3,
)
from andes_rl_kundur.control.classical_edge_residual import (
    ClassicalEdgeContract,
    compose_prior_residual_numpy,
    edge_severity_delta,
)
from andes_rl_kundur.control.vector_inertia_residual import EDGE_ENDPOINTS


class _ClassicalPriorMixin:
    classical_contract: ClassicalEdgeContract

    def _severity_delta_tensor(self, joint_obs: torch.Tensor) -> torch.Tensor:
        agent_obs = self._agent_obs_tensor(joint_obs)
        weights = torch.as_tensor(
            self.classical_contract.weights,
            dtype=agent_obs.dtype,
            device=agent_obs.device,
        )
        severity = torch.abs(agent_obs[:, :, [0, 1, 3]]) @ weights
        return torch.stack(
            [severity[:, target] - severity[:, source] for source, target in EDGE_ENDPOINTS],
            dim=-1,
        )

    def _compose_tensor(
        self,
        joint_obs: torch.Tensor,
        actor_residual: torch.Tensor,
    ) -> torch.Tensor:
        delta = self._severity_delta_tensor(joint_obs)
        prior = torch.tanh(self.classical_contract.gain * delta)
        magnitude = (
            torch.abs(prior)
            + self.classical_contract.residual_scale * actor_residual.clamp(-1.0, 1.0)
        ).clamp(-self.classical_contract.reverse_limit, 1.0)
        return torch.sign(delta) * magnitude

    def _select_with_prior(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool,
        rng: np.random.Generator | None,
    ) -> np.ndarray:
        obs = self._stack_observations(observations)
        joint = torch.as_tensor(
            obs.reshape(1, self.joint_obs_dim),
            dtype=torch.float32,
            device=self.device,
        )
        with torch.no_grad():
            residual = self._actor_residual(joint, self.actor).cpu().numpy().reshape(3)
        if not deterministic:
            generator = rng or np.random.default_rng()
            residual = residual + generator.normal(
                0.0,
                self.explore_noise,
                size=residual.shape,
            )
        return self._compose_numpy_and_record(obs, residual)

    def _compose_numpy_and_record(
        self,
        observations: np.ndarray,
        actor_residual: np.ndarray,
    ) -> np.ndarray:
        delta = edge_severity_delta(observations, self.classical_contract)
        prior = np.tanh(self.classical_contract.gain * delta).astype(np.float32)
        clipped_residual = np.clip(
            np.asarray(actor_residual, dtype=np.float32).reshape(3), -1.0, 1.0
        )
        action = compose_prior_residual_numpy(
            prior,
            clipped_residual,
            delta,
            residual_scale=self.classical_contract.residual_scale,
            reverse_limit=self.classical_contract.reverse_limit,
        )
        aligned = (np.sign(delta) * action).astype(np.float32)
        self.last_residual_composition = {
            "severity_delta": delta.astype(float).tolist(),
            "prior_raw": prior.astype(float).tolist(),
            "actor_residual": clipped_residual.astype(float).tolist(),
            "aligned_magnitude": aligned.astype(float).tolist(),
            "executed_edge_action": action.astype(float).tolist(),
            "reverse_count": int(np.sum(aligned < 0.0)),
            "reverse_limit": float(self.classical_contract.reverse_limit),
        }
        return action

    def compose_actor_residual(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        actor_residual: np.ndarray,
    ) -> np.ndarray:
        """Map an externally supplied residual through the frozen local prior."""

        obs = self._stack_observations(observations)
        return self._compose_numpy_and_record(obs, actor_residual)


class DistributedPriorResidualTD3(_ClassicalPriorMixin, DistributedEdgeTD3):
    """Shared one-hop edge actor whose output modulates a causal local prior."""

    algo_name = "distributed_prior_residual_td3"

    def __init__(
        self,
        *,
        classical_contract: ClassicalEdgeContract,
        **kwargs: object,
    ) -> None:
        self.classical_contract = classical_contract
        super().__init__(**kwargs)

    def _actor_residual(self, joint_obs: torch.Tensor, actor: nn.Module) -> torch.Tensor:
        return DistributedEdgeTD3._raw_actor(self, joint_obs, actor)

    def _raw_actor(self, joint_obs: torch.Tensor, actor: nn.Module) -> torch.Tensor:
        return self._compose_tensor(joint_obs, self._actor_residual(joint_obs, actor))

    def select_edge_actions(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        return self._select_with_prior(
            observations,
            deterministic=deterministic,
            rng=rng,
        )


class CentralPriorResidualTD3(_ClassicalPriorMixin, CentralVectorTD3):
    """Joint-observation actor over the identical classical edge prior."""

    algo_name = "central_prior_residual_td3"

    def __init__(
        self,
        *,
        classical_contract: ClassicalEdgeContract,
        **kwargs: object,
    ) -> None:
        self.classical_contract = classical_contract
        super().__init__(**kwargs)

    def _actor_residual(self, joint_obs: torch.Tensor, actor: nn.Module) -> torch.Tensor:
        return CentralVectorTD3._raw_actor(self, joint_obs, actor)

    def _raw_actor(self, joint_obs: torch.Tensor, actor: nn.Module) -> torch.Tensor:
        return self._compose_tensor(joint_obs, self._actor_residual(joint_obs, actor))

    def select_edge_actions(
        self,
        observations: dict[int, np.ndarray] | np.ndarray,
        *,
        deterministic: bool,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        return self._select_with_prior(
            observations,
            deterministic=deterministic,
            rng=rng,
        )
