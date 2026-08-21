"""Reference interface for a slew-consistent, Markov TD3 action channel.

This module is independent of ANDES.  It defines the *minimal* prospective E2
repair: preserve the historical actor output as a normalized **target action**,
append the previous executed action to the learner state, and apply the same
stateful target-to-executed projection in behavior, target-actor, online-actor,
critic, and replay semantics.

Time chain for transition k
---------------------------
base_obs_k, previous_executed_action_{k-1}
    -> augmented actor/critic state
    -> actor target action in [-1, 1]
    -> executed_action_k = project(previous, target, slew_limit)
    -> ANDES transition
    -> base_obs_{k+1}
    -> replay stores previous, target, executed, next observation

For a sampled next state, the previous executed action is exactly
``executed_action_k``.  The target actor must pass its noisy target through the
same differentiable projection before the target critic is queried.  The online
actor objective must do the same before the current critic is queried.

An increment-command parameterization is also supplied as an optional helper,
but it is *not* the minimal E2 causal intervention because it changes the actor
command semantics.  Treat it as a separately labelled follow-up, never bundle it
with the target-projection repair when estimating the effect of the historical
interface mismatch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import numpy as np
import torch

BASE_OBS_DIM: Final[int] = 7
ACTION_DIM: Final[int] = 2
AUGMENTED_OBS_DIM: Final[int] = BASE_OBS_DIM + ACTION_DIM
DEFAULT_SLEW_LIMIT: Final[float] = 0.25


def _validate_slew_limit(slew_limit: float) -> float:
    value = float(slew_limit)
    if not np.isfinite(value) or not 0.0 < value <= 2.0:
        raise ValueError("slew_limit must be finite and lie in (0, 2]")
    return value


def augment_actor_observation_np(
    base_observation: np.ndarray,
    previous_executed_action: np.ndarray,
) -> np.ndarray:
    """Append the two previous executed components to each seven-slot row."""

    obs = np.asarray(base_observation, dtype=np.float32)
    previous = np.asarray(previous_executed_action, dtype=np.float32)
    if obs.shape[-1] != BASE_OBS_DIM:
        raise ValueError(f"base observation last dimension must be {BASE_OBS_DIM}")
    if previous.shape != obs.shape[:-1] + (ACTION_DIM,):
        raise ValueError("previous action shape must match observation leading dimensions")
    if not np.all(np.isfinite(obs)) or not np.all(np.isfinite(previous)):
        raise ValueError("observations and previous actions must be finite")
    return np.concatenate([obs, previous], axis=-1).astype(np.float32)


def augment_actor_observation_torch(
    base_observation: torch.Tensor,
    previous_executed_action: torch.Tensor,
) -> torch.Tensor:
    if base_observation.shape[-1] != BASE_OBS_DIM:
        raise ValueError(f"base observation last dimension must be {BASE_OBS_DIM}")
    if previous_executed_action.shape != base_observation.shape[:-1] + (ACTION_DIM,):
        raise ValueError("previous action shape must match observation leading dimensions")
    return torch.cat([base_observation, previous_executed_action], dim=-1)


def project_target_np(
    previous_executed_action: np.ndarray,
    normalized_target_action: np.ndarray,
    *,
    slew_limit: float = DEFAULT_SLEW_LIMIT,
) -> np.ndarray:
    """Historical target-action semantics with explicit projector memory.

    This is the NumPy behavior/replay validator.  It matches the mathematical
    map used by ``LocalMDActionProjector`` up to its conservative float32
    one-ULP bookkeeping repair.
    """

    limit = _validate_slew_limit(slew_limit)
    previous = np.asarray(previous_executed_action, dtype=np.float32)
    target = np.asarray(normalized_target_action, dtype=np.float32)
    if previous.shape != target.shape or previous.shape[-1] != ACTION_DIM:
        raise ValueError("previous action and target must have equal shape (..., 2)")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(target)):
        raise ValueError("previous action and target must be finite")
    previous = np.clip(previous, -1.0, 1.0)
    target = np.clip(target, -1.0, 1.0)
    delta = np.clip(target - previous, -limit, limit)
    return np.clip(previous + delta, -1.0, 1.0).astype(np.float32)


def project_target_torch(
    previous_executed_action: torch.Tensor,
    normalized_target_action: torch.Tensor,
    *,
    slew_limit: float = DEFAULT_SLEW_LIMIT,
) -> torch.Tensor:
    """Almost-everywhere differentiable map for actor and target-actor paths."""

    limit = _validate_slew_limit(slew_limit)
    if previous_executed_action.shape != normalized_target_action.shape:
        raise ValueError("previous action and target must have equal shape")
    if previous_executed_action.shape[-1] != ACTION_DIM:
        raise ValueError("action last dimension must be 2")
    previous = previous_executed_action.clamp(-1.0, 1.0)
    target = normalized_target_action.clamp(-1.0, 1.0)
    delta = (target - previous).clamp(-limit, limit)
    return (previous + delta).clamp(-1.0, 1.0)


def execute_increment_np(
    previous_executed_action: np.ndarray,
    normalized_increment_command: np.ndarray,
    *,
    slew_limit: float = DEFAULT_SLEW_LIMIT,
) -> np.ndarray:
    """Optional increment parameterization; not the minimal E2 intervention."""

    limit = _validate_slew_limit(slew_limit)
    previous = np.asarray(previous_executed_action, dtype=np.float32)
    command = np.asarray(normalized_increment_command, dtype=np.float32)
    if previous.shape != command.shape or previous.shape[-1] != ACTION_DIM:
        raise ValueError("previous action and command must have equal shape (..., 2)")
    if not np.all(np.isfinite(previous)) or not np.all(np.isfinite(command)):
        raise ValueError("previous action and command must be finite")
    command = np.clip(command, -1.0, 1.0)
    return np.clip(previous + limit * command, -1.0, 1.0).astype(np.float32)


def execute_increment_torch(
    previous_executed_action: torch.Tensor,
    normalized_increment_command: torch.Tensor,
    *,
    slew_limit: float = DEFAULT_SLEW_LIMIT,
) -> torch.Tensor:
    """Optional differentiable increment parameterization."""

    limit = _validate_slew_limit(slew_limit)
    if previous_executed_action.shape != normalized_increment_command.shape:
        raise ValueError("previous action and command must have equal shape")
    if previous_executed_action.shape[-1] != ACTION_DIM:
        raise ValueError("action last dimension must be 2")
    command = normalized_increment_command.clamp(-1.0, 1.0)
    return (previous_executed_action + limit * command).clamp(-1.0, 1.0)


@dataclass(frozen=True)
class SlewAwareTransition:
    """Minimal replay fields required to preserve projector-state semantics."""

    base_observation: np.ndarray
    previous_executed_action: np.ndarray
    normalized_target_action: np.ndarray
    executed_action: np.ndarray
    next_base_observation: np.ndarray
    done: bool

    def validate(
        self,
        *,
        slew_limit: float = DEFAULT_SLEW_LIMIT,
        atol: float = 2e-7,
    ) -> None:
        expected = project_target_np(
            self.previous_executed_action,
            self.normalized_target_action,
            slew_limit=slew_limit,
        )
        actual = np.asarray(self.executed_action, dtype=np.float32)
        if actual.shape != expected.shape:
            raise ValueError("executed_action shape mismatch")
        if not np.allclose(actual, expected, rtol=0.0, atol=atol):
            raise ValueError("executed_action is inconsistent with previous action and target")
        previous = np.asarray(self.previous_executed_action, dtype=np.float32)
        if np.any(np.abs(actual - previous) > slew_limit + atol):
            raise ValueError("executed_action violates slew limit")


def target_previous_action(current_executed_action: torch.Tensor) -> torch.Tensor:
    """The next state's projector memory is the sampled current executed action."""

    if current_executed_action.shape[-1] != ACTION_DIM:
        raise ValueError("current executed action last dimension must be 2")
    return current_executed_action


__all__ = [
    "ACTION_DIM",
    "AUGMENTED_OBS_DIM",
    "BASE_OBS_DIM",
    "DEFAULT_SLEW_LIMIT",
    "SlewAwareTransition",
    "augment_actor_observation_np",
    "augment_actor_observation_torch",
    "execute_increment_np",
    "execute_increment_torch",
    "project_target_np",
    "project_target_torch",
    "target_previous_action",
]
