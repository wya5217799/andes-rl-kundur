"""Directed tests for the R422 common-channel repair runner.

Windows-safe: constants, agent factory (unchanged R419 bundle), the
common-channel effort-augmented cost math, and the contract shape.  The
WSL-only lifecycle runs through the scratch launcher in the sealed round
itself.  Scratch pre-draft: the runner is not executed until its own round
is reserved, planned, rehearsed, and sealed.
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

import run_r422_common_channel_repair as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
)


def test_constants_frozen() -> None:
    assert runner.ACTION_EFFORT_WEIGHT == 1.0
    assert runner.ROUND_ID == "R422"


def test_agent_factory_unchanged_bundle() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, SlewAwareCDMATD3)
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_common_channel_effort_cost() -> None:
    contract = runner.build_contract()
    frequencies = np.array([[60.05, 60.02, 59.98, 59.96]])
    rocof = np.array([[0.1, 0.05, -0.05, -0.1]])
    p_es = np.array([[0.01, 0.01, -0.01, -0.01]])
    action = np.array([[0.5, 0.5], [0.5, 0.5], [0.5, 0.5], [0.5, 0.5]])
    differential, common, effort = runner._common_channel_costs(
        frequencies, rocof, p_es, action, contract
    )
    # effort = mean over agents of squared 2-norm = 0.5^2 + 0.5^2 = 0.5
    assert abs(effort - 0.5) < 1e-9
    # common channel carries the weighted effort, differential does not
    from andes_rl_kundur.agents.cd_matd3 import physical_costs

    plain_differential, plain_common = physical_costs(
        frequencies, rocof, p_es, contract=contract
    )
    assert abs(differential - float(plain_differential[0])) < 1e-12
    assert abs(common - (float(plain_common[0]) + runner.ACTION_EFFORT_WEIGHT * effort)) < 1e-12
    assert float(plain_common[0]) > 0.0
    assert np.isfinite(common)


def test_zero_action_keeps_plain_cost() -> None:
    contract = runner.build_contract()
    frequencies = np.array([[60.05, 60.02, 59.98, 59.96]])
    rocof = np.array([[0.1, 0.05, -0.05, -0.1]])
    p_es = np.array([[0.01, 0.01, -0.01, -0.01]])
    action = np.zeros((4, 2))
    differential, common, effort = runner._common_channel_costs(
        frequencies, rocof, p_es, action, contract
    )
    assert abs(effort) < 1e-12
    from andes_rl_kundur.agents.cd_matd3 import physical_costs

    plain_differential, plain_common = physical_costs(
        frequencies, rocof, p_es, contract=contract
    )
    assert abs(common - float(plain_common[0])) < 1e-12


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
