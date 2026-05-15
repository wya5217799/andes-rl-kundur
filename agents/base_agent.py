"""Structural interface every per-agent algorithm in this repo satisfies.

Both ``SACAgent`` (independent SAC) and ``SACAgentCTDE`` (decentralized
actor + shared critic) already match this Protocol at runtime — they
do not need to inherit from it. Code that wants to be algorithm-agnostic
(e.g., a training loop that supports ``--algo sac`` and a future ``td3``)
can type-hint against this Protocol without coupling to any concrete
class.

Adding a new algorithm:
    1. Create ``agents/<algo>.py`` whose class exposes these methods
       with the same signatures.
    2. Add a branch in the training-loop factory that constructs it.
    3. The trainer needs no other changes.

Off-policy algorithms (SAC, TD3, DDPG) fit cleanly. On-policy algorithms
(PPO) do not — they don't have a per-transition replay buffer. A future
PPO addition will require a sibling Protocol or a small refactor of the
trainer's update loop; deferred until that experiment is on the table.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class BaseAgent(Protocol):
    """Per-agent control loop surface for off-policy MARL."""

    def select_action(
        self,
        obs: np.ndarray,
        deterministic: bool = False,
    ) -> np.ndarray:
        """Return action in ``[-1, 1]`` of shape ``(action_dim,)``."""
        ...

    def store_transition(
        self,
        obs: np.ndarray,
        action: np.ndarray,
        reward: float,
        next_obs: np.ndarray,
        done: bool,
    ) -> None:
        """Append a transition to the replay buffer."""
        ...

    def update(self) -> dict | None:
        """Run one optimization step. Returns loss dict, or ``None`` if
        the buffer is below the batch threshold."""
        ...

    def save(self, path: str) -> None:
        """Persist the agent's full state to ``path``."""
        ...

    def load(self, path: str) -> dict:
        """Restore agent state. Returns the ``metadata`` dict that was
        saved alongside, or ``{}`` if none."""
        ...
