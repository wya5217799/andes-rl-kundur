"""Directed tests for the R427 critic target normalization runner.

Windows-safe: constants, the agent factory (CD arms -> P1 subclass,
scalar arm -> unchanged R419 class), the R419-verbatim reward seam, the
normalization semantics probe helper, the quartile-readout helper, and
the contract shape.  The WSL-only lifecycle runs through the scratch
launcher in the sealed round itself.
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

import run_r427_critic_target_normalization as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareYangScalarTD3,
    physical_costs,
)
from andes_rl_kundur.agents.cd_matd3_critic_norm import (  # noqa: E402
    CRITIC_NORM_BETA,
    CRITIC_NORM_MU_INIT,
    CRITIC_NORM_SIGMA_INIT,
    CRITIC_NORM_SIGMA_MIN,
    PopArtDifferentialCriticSlewAwareCDMATD3Signfix,
)


def test_constants_frozen() -> None:
    assert runner.ROUND_ID == "R427"
    assert runner.OTHER_RESERVED_PROCESSES == 0
    assert runner.ACTION_RMS_HARM_FACTOR == 1.10
    assert runner.ACTION_TV_HARM_FACTOR == 1.10
    assert runner.TIER1_TOTAL_STEPS == 8640
    assert CRITIC_NORM_BETA == 1.0e-3
    assert CRITIC_NORM_SIGMA_MIN == 1.0e-4
    assert CRITIC_NORM_MU_INIT == 0.0
    assert CRITIC_NORM_SIGMA_INIT == 1.0


def test_agent_factory_mapping() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, PopArtDifferentialCriticSlewAwareCDMATD3Signfix)
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(
        no_message, PopArtDifferentialCriticSlewAwareCDMATD3Signfix
    )
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    assert not isinstance(
        scalar, PopArtDifferentialCriticSlewAwareCDMATD3Signfix
    )
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_reward_seam_r419_verbatim() -> None:
    contract = runner.build_contract()
    frequencies = np.array([[60.05, 60.02, 59.98, 59.96]])
    rocof = np.array([[0.1, 0.05, -0.05, -0.1]])
    p_es = np.array([[0.01, 0.01, -0.01, -0.01]])
    differential, common = runner._cd_step_costs(
        frequencies, rocof, p_es, contract
    )
    plain_differential, plain_common = physical_costs(
        frequencies, rocof, p_es, contract=contract
    )
    assert abs(differential - float(plain_differential[0])) < 1e-12
    assert abs(common - float(plain_common[0])) < 1e-12


def test_normalization_semantics_probe_helper() -> None:
    # The plan-declared semantics gate must run on the real learner
    # (tensor-only; no ANDES import) and must not raise.
    agent = runner._agent_for("cd_matd3_message", "cpu")
    agent.guard_multiplier_step(0.5, 0.5)  # inherited constraint seam
    probe = runner._rehearsal_normalization_semantics_check(agent)
    assert probe["output_correction_identity"]["ok"] is True
    assert probe["common_target_untouched"]["ok"] is True
    assert probe["differential_gradient_dot"] > 0.0
    assert probe["differential_gradient_decomposition_ok"] is True
    assert probe["stats_convergence"]["ok"] is True
    # The probe must restore the policy noise (no silent agent mutation).
    assert agent.policy_noise == 0.2


def test_quartile_ratio_helper() -> None:
    flat = [1.0] * 40 + [4.0] * 40
    readout = runner._quartile_ratio(flat)
    assert readout["q1"] == pytest.approx(1.0)
    assert readout["q4"] == pytest.approx(4.0)
    assert readout["ratio"] == pytest.approx(4.0)
    growing = list(range(1, 101))
    readout = runner._quartile_ratio(growing)
    assert readout["q4"] > readout["q1"]
    assert readout["ratio"] > 1.0
    empty = runner._quartile_ratio([])
    assert empty["count"] == 0
    assert empty["ratio"] is None


def test_tier1_arm_filter_parsing() -> None:
    # R427 tier1 race lesson: argparse REMAINDER swallows --arm after the
    # positional command, so the arm filter is resolved from args.args.
    assert runner._tier1_arm_from(["cd_matd3_message"]) == "cd_matd3_message"
    assert (
        runner._tier1_arm_from(["--arm", "cd_matd3_no_message"])
        == "cd_matd3_no_message"
    )
    assert runner._tier1_arm_from([]) is None
    assert runner._tier1_arm_from(["--seed", "401"]) is None


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
    assert (
        contract["training_contract"]["total_interaction_steps"]
        == 43200
    )


def test_shared_core_config_binding() -> None:
    # The formal wrapper and the Tier-1 wrapper bind different configs
    # onto one shared loop: pin the budget/root/anchor differences here
    # so a future edit cannot silently unify them.
    contract = runner.build_contract()
    formal_steps = int(
        contract["training_contract"]["total_interaction_steps"]
    )
    assert formal_steps == 43200
    assert runner.TIER1_TOTAL_STEPS == 8640
    assert formal_steps // 5 == runner.TIER1_TOTAL_STEPS
    assert "tmp" in runner.TIER1_OUT.parts
    assert runner.OUT.parts[-1] == "r427_critic_target_normalization"
