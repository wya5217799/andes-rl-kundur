"""R438 runner drift-pinning tests (Windows-safe, no ANDES import).

Pins the decoupled channel semantics: obs-only reward equals the R431
masked reference, rew-only differs by the neighbour term, both
non-positive; contract shape; channel wrapper obs masking.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

_spec = importlib.util.spec_from_file_location(
    "_r438_runner", ROOT / "scripts/run_r438_sac_message_channels.py"
)
r438 = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = r438
_spec.loader.exec_module(r438)


def _synthetic_obs() -> np.ndarray:
    rows = np.zeros((4, 7), dtype=np.float32)
    rows[:, 1] = 0.1
    rows[:, 3] = 0.05
    rows[:, 4] = -0.05
    return rows


def test_contract_frozen_shape() -> None:
    contract = r438.build_contract()
    assert contract["r438"]["channel_arms"] == list(r438.CHANNEL_ARMS)
    assert contract["r438"]["training_seeds"] == r438.TRAINING_SEEDS
    assert contract["r438"]["same_side_tolerance"] == 0.10
    assert len(contract["profiles"]) == 8


def test_obs_only_reward_matches_r431_masked() -> None:
    obs = _synthetic_obs()
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    r_obs_only = r438.channel_step_rewards(obs, dm, dd, rew_masked=True)
    reference = r438.r431._sac_step_rewards(obs, dm, dd, masked=True)
    assert np.allclose(r_obs_only, reference, atol=1.0e-6)


def test_rew_only_reward_differs_by_neighbour_term() -> None:
    obs = _synthetic_obs()
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    r_rew_only = r438.channel_step_rewards(obs, dm, dd, rew_masked=False)
    r_obs_only = r438.channel_step_rewards(obs, dm, dd, rew_masked=True)
    assert not np.allclose(r_rew_only, r_obs_only, atol=1.0e-6)
    # with neighbours present, eta=1 must lower r_f (more negative) than eta=0
    assert float(np.sum(r_rew_only)) < float(np.sum(r_obs_only))


def test_rewards_nonpositive() -> None:
    obs = _synthetic_obs()
    dm = np.array([600.0, -200.0, 0.0, 0.0])
    dd = np.array([600.0, -200.0, 0.0, 0.0])
    for rew_masked in (True, False):
        rewards = r438.channel_step_rewards(obs, dm, dd, rew_masked=rew_masked)
        assert np.all(rewards <= 1.0e-9)
        assert np.all(np.isfinite(rewards))


def test_wrapper_obs_masking() -> None:
    obs_only = r438.ChannelSACArmWrapper(obs_masked=False, rew_masked=True)
    rew_only = r438.ChannelSACArmWrapper(obs_masked=True, rew_masked=False)
    assert not obs_only.obs_masked and obs_only.rew_masked
    assert rew_only.obs_masked and not rew_only.rew_masked
    joint = np.zeros((4, 7), dtype=np.float32)
    joint[:, 3] = 0.5
    rows = rew_only._rows(joint)
    assert np.all(rows[:, 3:7] == 0.0)
    rows_full = obs_only._rows(joint)
    assert np.all(rows_full[:, 3] == 0.5)


def test_agent_for_arms() -> None:
    obs_only = r438.agent_for(r438.OBS_ONLY_ARM, "cpu")
    rew_only = r438.agent_for(r438.REW_ONLY_ARM, "cpu")
    assert obs_only.obs_masked is False and obs_only.rew_masked is True
    assert rew_only.obs_masked is True and rew_only.rew_masked is False
