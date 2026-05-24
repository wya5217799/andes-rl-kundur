"""``EpisodeResult`` dataclass replaces the dict-with-string-keys that
``scripts/train.py:run_episode`` used to return. The typed shape makes
field typos a static error and gives callers IDE auto-complete.

Tracer behaviour: import the dataclass + verify field set.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def test_episode_result_exposes_named_fields():
    """Tracer: every field the training loop used to look up by string
    is now an attribute on the dataclass."""
    from andes_rl_kundur.agents.episode_result import EpisodeResult

    expected = {
        "reset_failed", "ep_reward", "ep_r_f", "ep_r_h", "ep_r_d",
        "ep_actions", "ep_max_freq", "ep_tds_failed", "total_steps",
    }
    actual = set(EpisodeResult.__dataclass_fields__.keys())
    assert expected <= actual, f"missing fields: {expected - actual}"


def test_episode_result_carries_optional_reason_when_reset_failed():
    """If reset failed, a human-readable reason string lives on the
    record. Pre-refactor train.py read ``stats['reason']`` after a
    failed reset — the string key existed only when reset_failed=True,
    making static checking impossible."""
    from andes_rl_kundur.agents.episode_result import EpisodeResult

    ok = EpisodeResult(
        reset_failed=False,
        ep_reward={0: 0.0, 1: 0.0, 2: 0.0, 3: 0.0},
        ep_r_f=0.0, ep_r_h=0.0, ep_r_d=0.0,
        ep_actions=[np.zeros((4, 2), dtype=np.float32)],
        ep_max_freq=0.0,
        ep_tds_failed=False,
        total_steps=50,
    )
    assert ok.reset_failed is False
    assert ok.reason is None

    bad = EpisodeResult.from_reset_failure("ANDES TDS busted")
    assert bad.reset_failed is True
    assert bad.reason == "ANDES TDS busted"


def test_episode_result_to_monitor_kwargs():
    """Adapter from EpisodeResult into the 6-kwarg shape that
    ``TrainingMonitor.log_and_check`` expects.
    """
    from andes_rl_kundur.agents.episode_result import EpisodeResult

    actions = [np.zeros((4, 2), dtype=np.float32) for _ in range(50)]
    er = EpisodeResult(
        reset_failed=False,
        ep_reward={0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0},
        ep_r_f=10.0, ep_r_h=-5.0, ep_r_d=-2.0,
        ep_actions=actions,
        ep_max_freq=0.15,
        ep_tds_failed=False,
        total_steps=50,
    )
    kwargs = er.to_monitor_kwargs()
    assert kwargs["rewards"] == 10.0  # sum(ep_reward.values())
    assert kwargs["reward_components"] == {"r_f": 10.0, "r_h": -5.0, "r_d": -2.0}
    assert kwargs["info"] == {
        "tds_failed": False, "max_freq_deviation_hz": 0.15,
    }
    assert kwargs["per_agent_rewards"] == {0: 1.0, 1: 2.0, 2: 3.0, 3: 4.0}
    assert kwargs["actions"].shape == (50, 4, 2)
