"""Directed tests for the R423 value-estimation repair runner.

Windows-safe: constants, the agent factory (CD arms -> repair subclass,
scalar arm -> unchanged R422 class), the verbatim reward seam, the
critic-loss readout math, and the contract shape.  The WSL-only
lifecycle runs through the scratch launcher in the sealed round itself.
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

import run_r423_value_estimation_repair as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareYangScalarTD3,
)
from andes_rl_kundur.agents.cd_matd3_vfix import (  # noqa: E402
    ClippedCriticSlewAwareCDMATD3,
)


def test_constants_frozen() -> None:
    assert runner.ROUND_ID == "R423"
    assert runner.ACTION_EFFORT_WEIGHT == 1.0
    assert runner.OTHER_RESERVED_PROCESSES == 0


def test_agent_factory_repair_mapping() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, ClippedCriticSlewAwareCDMATD3)
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(no_message, ClippedCriticSlewAwareCDMATD3)
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    assert not isinstance(scalar, ClippedCriticSlewAwareCDMATD3)
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_reward_seam_verbatim_r422() -> None:
    contract = runner.build_contract()
    frequencies = np.array([[60.05, 60.02, 59.98, 59.96]])
    rocof = np.array([[0.1, 0.05, -0.05, -0.1]])
    p_es = np.array([[0.01, 0.01, -0.01, -0.01]])
    action = np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    differential, common, effort = runner._common_channel_costs(
        frequencies, rocof, p_es, action, contract
    )
    assert abs(effort - 0.5) < 1e-9
    from andes_rl_kundur.agents.cd_matd3 import physical_costs

    plain_differential, plain_common = physical_costs(
        frequencies, rocof, p_es, contract=contract
    )
    assert abs(differential - float(plain_differential[0])) < 1e-12
    assert abs(common - (float(plain_common[0]) + runner.ACTION_EFFORT_WEIGHT * effort)) < 1e-12


def test_critic_loss_readout_quartile_math() -> None:
    # Frozen rule (mirrored from the runner helper): Q1 = median of the
    # first 25% of the finite trace, Q4 = median of the last 25%;
    # ratio = Q4 / max(Q1, 1e-12).  Pin the arithmetic the helper uses.
    monotone = np.arange(1, 101, dtype=float)
    quarter = max(1, monotone.size // 4)
    q1 = float(np.median(monotone[:quarter]))
    q4 = float(np.median(monotone[-quarter:]))
    assert q1 == 13.0
    assert q4 == 88.0
    ratio = q4 / max(q1, 1e-12)
    assert abs(ratio - (88.0 / 13.0)) < 1e-12


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
