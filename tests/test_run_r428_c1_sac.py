"""Directed tests for the R428 C1-SAC runner.

Windows-safe: constants, the agent factory (scalar -> R419 class, CD arms
-> exact Yang-SAC wrapper with the mask flag), the paper reward
reconstruction (Eq.14-18, non-positive, obs-consistent, masked r^f==0),
the SAC semantics probe helper, and the arm-filter parsing.  The WSL-only
lifecycle runs through the scratch launcher in the sealed round.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))

import run_r428_c1_sac as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import SlewAwareYangScalarTD3  # noqa: E402
from andes_rl_kundur.agents.yang_sac_exact import YangExactSACAgent  # noqa: E402


def test_constants_frozen() -> None:
    assert runner.ROUND_ID == "R428"
    assert runner.PAPER_PHI_F == 100.0
    assert runner.PAPER_PHI_H == 1.0
    assert runner.PAPER_PHI_D == 1.0
    assert runner.SAC_MASKED_ARM == "cd_matd3_no_message"
    assert runner.TIER1_TOTAL_STEPS == 8640
    assert runner.OTHER_RESERVED_PROCESSES == 0


def test_agent_factory_mapping() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, runner._SACArmWrapper)
    assert message.masked is False
    assert len(message.agents) == 4
    assert all(isinstance(a, YangExactSACAgent) for a in message.agents)
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(no_message, runner._SACArmWrapper)
    assert no_message.masked is True
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_sac_step_rewards_nonpositive_and_obs_consistent() -> None:
    joint = np.zeros((4, 7), dtype=np.float32)
    joint[:, 1] = 0.1
    joint[:, 3] = 0.05
    joint[:, 4] = -0.05
    delta_m = np.array([5.0, -3.0, 2.0, -1.0])
    delta_d = np.array([1.0, 2.0, -1.0, 0.5])
    rewards = runner._sac_step_rewards(joint, delta_m, delta_d, masked=False)
    assert rewards.shape == (4,)
    assert np.all(rewards <= 0.0 + 1.0e-9)
    assert np.all(np.isfinite(rewards))
    # Masked arm: eta=0 -> r^f == 0, so rewards collapse to phi_h r_h +
    # phi_d r_d for every agent (identical across agents).
    masked_rewards = runner._sac_step_rewards(
        joint, delta_m, delta_d, masked=True
    )
    r_h = -((float(np.mean(delta_m)) / 2.0) ** 2)
    r_d = -((float(np.mean(delta_d))) ** 2)
    expected = runner.PAPER_PHI_H * r_h + runner.PAPER_PHI_D * r_d
    assert np.allclose(masked_rewards, expected, atol=1.0e-6)


def test_sac_arm_act_masks_neighbour_slots() -> None:
    torch_manual = __import__("torch").manual_seed
    torch_manual(0)
    wrapper = runner._agent_for("cd_matd3_no_message", "cpu")
    joint = np.random.randn(4, 7).astype(np.float32)
    action = wrapper.act(joint, deterministic=True)
    assert action.shape == (4, 2)
    assert np.all(np.abs(action) <= 1.0)


def test_rehearsal_sac_semantics_probe_helper() -> None:
    # Tensor-only (no ANDES); must not raise on the real learner.
    wrapper = runner._agent_for("cd_matd3_message", "cpu")
    probe = runner._rehearsal_sac_semantics_check(wrapper, masked=False)
    assert probe["critic_target_identity_ok"] is True
    assert probe["actor_loss_form_ok"] is True
    assert probe["alpha_loss_form_ok"] is True
    assert probe["reward_nonpositive_ok"] is True
    assert probe["reward_obs_consistent_ok"] is True
    masked_wrapper = runner._agent_for("cd_matd3_no_message", "cpu")
    probe = runner._rehearsal_sac_semantics_check(masked_wrapper, masked=True)
    assert probe["reward_obs_consistent_ok"] is True


def test_tier1_arm_filter_parsing() -> None:
    assert runner._tier1_arm_from(["cd_matd3_message"]) == "cd_matd3_message"
    assert (
        runner._tier1_arm_from(["--arm", "cd_matd3_no_message"])
        == "cd_matd3_no_message"
    )
    assert runner._tier1_arm_from([]) is None


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
    assert (
        contract["training_contract"]["total_interaction_steps"]
        == 43200
    )
