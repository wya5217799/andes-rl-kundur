"""Training adapter for a bounded learned residual around physical droop."""

from __future__ import annotations

from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.hybrid import (
    compose_bounded_droop_residual_actions,
    proportional_damping_action_fn,
)


class BoundedDroopResidualEnv:
    """Interpret agent actions as residuals while delegating physics to V4.

    Replay buffers retain the raw residual selected by the agent because the
    outer training loop owns replay insertion.  The wrapped V4 environment
    receives the composed action and therefore computes dynamics, reward,
    action observation, physical clipping, and failure status from the action
    that is actually deployed.
    """

    def __init__(
        self,
        env: Any,
        *,
        k_droop: float,
        residual_scale: float,
    ) -> None:
        self._env = env
        self.k_droop = float(k_droop)
        self.residual_scale = float(residual_scale)
        # Eager validation through the shared pure composer dependencies.
        proportional_damping_action_fn(self.k_droop)
        if not np.isfinite(self.residual_scale) or not 0.0 <= self.residual_scale <= 1.0:
            raise ValueError(
                "residual_scale must be finite and in [0, 1], "
                f"got {residual_scale!r}"
            )
        self._current_obs: dict[int, np.ndarray] | None = None
        self.last_prior_actions: dict[int, np.ndarray] | None = None
        self.last_residual_actions: dict[int, np.ndarray] | None = None
        self.last_executed_actions: dict[int, np.ndarray] | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self._env, name)

    @property
    def controller_contract(self) -> dict[str, Any]:
        return {
            "mode": "bounded_droop_residual",
            "k_droop": self.k_droop,
            "residual_scale": self.residual_scale,
            "composition": "clip(droop + residual_scale * residual, -1, 1)",
        }

    def reset(self, *args: Any, **kwargs: Any) -> dict[int, np.ndarray]:
        obs = self._env.reset(*args, **kwargs)
        self._current_obs = obs
        self.last_prior_actions = None
        self.last_residual_actions = None
        self.last_executed_actions = None
        return obs

    def step(
        self,
        residual_actions: dict[int, np.ndarray],
    ) -> tuple[dict[int, np.ndarray], dict[int, float], bool, dict[str, Any]]:
        if self._current_obs is None:
            raise RuntimeError("reset() must be called before step()")
        n_agents = int(self._env.N_AGENTS)
        prior = proportional_damping_action_fn(self.k_droop)(
            0,
            self._current_obs,
            n_agents,
        )
        executed = compose_bounded_droop_residual_actions(
            self._current_obs,
            residual_actions,
            n_agents=n_agents,
            k_droop=self.k_droop,
            residual_scale=self.residual_scale,
        )
        next_obs, rewards, done, info = self._env.step(executed)
        self._current_obs = next_obs
        self.last_prior_actions = {
            i: np.asarray(prior[i], dtype=np.float32).copy() for i in range(n_agents)
        }
        self.last_residual_actions = {
            i: np.clip(np.asarray(residual_actions[i], dtype=np.float32), -1.0, 1.0)
            for i in range(n_agents)
        }
        self.last_executed_actions = {
            i: np.asarray(executed[i], dtype=np.float32).copy() for i in range(n_agents)
        }
        enriched = dict(info)
        enriched["controller_contract"] = self.controller_contract
        enriched["residual_action_linf"] = float(
            max(np.max(np.abs(action)) for action in self.last_residual_actions.values())
        )
        enriched["executed_action_linf"] = float(
            max(np.max(np.abs(action)) for action in self.last_executed_actions.values())
        )
        return next_obs, rewards, done, enriched

    def close(self) -> Any:
        return self._env.close()
