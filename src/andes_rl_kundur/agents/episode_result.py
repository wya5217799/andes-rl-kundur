"""Per-episode summary record produced by the training loop.

Replaces the dict-with-string-keys that ``scripts/train.py:run_episode``
used to return (``"ep_reward"``, ``"ep_r_f"``, …). String-keyed dicts
let typos through silently and gave the monitor adapter a 7-kwarg
signature with no static checking. ``EpisodeResult`` makes every
field explicit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class EpisodeResult:
    """Summary of one training episode.

    ``reset_failed=True`` short-circuits the rest of the fields.
    """

    reset_failed: bool

    ep_reward: dict[int, float] = field(default_factory=dict)
    ep_r_f: float = 0.0
    ep_r_h: float = 0.0
    ep_r_d: float = 0.0
    ep_actions: list[np.ndarray] = field(default_factory=list)
    ep_max_freq: float = 0.0
    ep_tds_failed: bool = False
    total_steps: int = 0

    reason: str | None = None  # only set when reset_failed=True

    @classmethod
    def from_reset_failure(cls, reason: str, total_steps: int = 0) -> "EpisodeResult":
        """Build the short-circuit record used when ``env.reset()`` raises."""
        return cls(reset_failed=True, reason=reason, total_steps=total_steps)

    def to_monitor_kwargs(self) -> dict[str, Any]:
        """Adapter for ``TrainingMonitor.log_and_check``.

        The monitor accepts six keyword arguments; this method packs the
        EpisodeResult fields into exactly that shape so the call site
        does not have to enumerate them.
        """
        return {
            "rewards": sum(self.ep_reward.values()),
            "reward_components": {
                "r_f": self.ep_r_f, "r_h": self.ep_r_h, "r_d": self.ep_r_d,
            },
            "actions": np.array(self.ep_actions),
            "info": {
                "tds_failed": self.ep_tds_failed,
                "max_freq_deviation_hz": self.ep_max_freq,
            },
            "per_agent_rewards": self.ep_reward,
        }
