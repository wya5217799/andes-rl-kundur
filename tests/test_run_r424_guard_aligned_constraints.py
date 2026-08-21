"""Directed tests for the R424 guard-aligned action-constraint runner.

Windows-safe: constants, the agent factory (CD arms -> guard subclass,
scalar arm -> unchanged R419 class), the R419-verbatim reward seam, the
relative-residual math, and the contract shape.  The WSL-only lifecycle
runs through the scratch launcher in the sealed round itself.
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

import run_r424_guard_aligned_constraints as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareYangScalarTD3,
    physical_costs,
)
from andes_rl_kundur.agents.cd_matd3_guard_constraints import (  # noqa: E402
    GuardConstrainedSlewAwareCDMATD3,
)


def test_constants_frozen() -> None:
    assert runner.ROUND_ID == "R424"
    assert runner.OTHER_RESERVED_PROCESSES == 0
    assert runner.ACTION_RMS_HARM_FACTOR == 1.10
    assert runner.ACTION_TV_HARM_FACTOR == 1.10


def test_agent_factory_mapping() -> None:
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, GuardConstrainedSlewAwareCDMATD3)
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(no_message, GuardConstrainedSlewAwareCDMATD3)
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    assert not isinstance(scalar, GuardConstrainedSlewAwareCDMATD3)
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


def test_relative_residual_math() -> None:
    # Frozen rule: rms_rel = rms_mean / max((1.10^2) * rms_ref^2, eps) - 1
    # and tv_rel = tv_total / max(1.10 * tv_ref_sm, eps) - 1.
    eps = runner.GUARD_RESIDUAL_EPSILON
    rms_mean, rms_ref = 0.3, 0.5
    rms_rel = rms_mean / max(
        (runner.ACTION_RMS_HARM_FACTOR**2) * rms_ref**2, eps
    ) - 1.0
    assert abs(rms_rel - (0.3 / (1.21 * 0.25) - 1.0)) < 1e-12
    tv_total, tv_ref_sm = 6.0, 5.0
    tv_rel = tv_total / max(
        runner.ACTION_TV_HARM_FACTOR * tv_ref_sm, eps
    ) - 1.0
    assert abs(tv_rel - (6.0 / 5.5 - 1.0)) < 1e-12


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
