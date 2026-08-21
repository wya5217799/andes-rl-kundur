"""Directed tests for the R420 objective-repair runner.

Windows-safe: constants, agent factory (unchanged R419 bundle), the
effort-augmented cost math, and the shard-id contract.  The WSL-only
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

import run_r420_objective_repair as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
    physical_costs_with_action_effort,
)


def test_constants_frozen() -> None:
    assert runner.ACTION_EFFORT_WEIGHT == 1.0
    assert runner.ROUND_ID == "R420"


def test_agent_factory_unchanged_bundle() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, SlewAwareCDMATD3)
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_effort_augmented_cost() -> None:
    contract = runner.build_contract()
    frequencies = np.array([[60.05, 60.02, 59.98, 59.96]])
    rocof = np.array([[0.1, 0.05, -0.05, -0.1]])
    p_es = np.array([[0.01, 0.01, -0.01, -0.01]])
    actions = np.array([[[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]]])
    repaired, common, effort = physical_costs_with_action_effort(
        frequencies,
        rocof,
        p_es,
        actions,
        contract=contract,
        action_weight=runner.ACTION_EFFORT_WEIGHT,
    )
    # effort = mean over agents of squared 2-norm = 0.5^2 + 0.5^2 = 0.5
    assert abs(float(effort[0]) - 0.5) < 1e-9
    assert float(repaired[0]) > 0.0
    assert np.isfinite(float(common[0]))


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
