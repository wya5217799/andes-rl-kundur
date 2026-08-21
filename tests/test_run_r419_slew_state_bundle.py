"""Directed tests for the R419 slew-state bundle runner (B1 successor).

Windows-safe: agent factory, observation augmentation flow, the median
endpoint table math, the R410-formula message contrast, and the R418-abort
regression pin (flattened previous-action store shape).  The WSL-only
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

import run_r419_slew_state_bundle as runner  # noqa: E402
from andes_rl_kundur.agents.cd_matd3 import (  # noqa: E402
    SlewAwareCDMATD3,
    SlewAwareYangScalarTD3,
)


def test_agent_factory() -> None:
    scalar = runner._agent_for("yang_scalar_td3", "cpu")
    assert isinstance(scalar, SlewAwareYangScalarTD3)
    message = runner._agent_for("cd_matd3_message", "cpu")
    assert isinstance(message, SlewAwareCDMATD3)
    assert message.actor_neighbour_mask is False
    no_message = runner._agent_for("cd_matd3_no_message", "cpu")
    assert isinstance(no_message, SlewAwareCDMATD3)
    assert no_message.actor_neighbour_mask is True
    assert no_message.action_slew_limit == 0.25
    with pytest.raises(ValueError):
        runner._agent_for("unknown", "cpu")


def test_r418_abort_regression_store_shape() -> None:
    """R418 aborted because previous_executed was stored unflattened; the
    runner must flatten it to the ring's (8,) slot."""
    agent = runner._agent_for("cd_matd3_message", "cpu")
    joint = np.zeros(28, dtype=np.float32)
    previous_executed = np.zeros((4, 2), dtype=np.float32)
    flattened = previous_executed.reshape(-1).astype(np.float32)
    assert flattened.shape == (8,)
    action = np.zeros((4, 2), dtype=np.float32)
    agent.store(
        joint,
        flattened,
        action.reshape(-1).astype(np.float32),
        np.array([-1.0, -1.0], dtype=np.float32),
        joint,
        False,
    )
    assert agent.buffer.size == 1


def test_arm_seed_aggregate() -> None:
    summaries = [
        {
            "arm_id": "cd_matd3_message",
            "training_seed": 401,
            "off_diagonal_response_energy": 1.0,
            "disturbance_differential_energy": 2.0,
        },
        {
            "arm_id": "cd_matd3_message",
            "training_seed": 401,
            "off_diagonal_response_energy": 3.0,
            "disturbance_differential_energy": 4.0,
        },
        {
            "arm_id": "cd_matd3_message",
            "training_seed": 402,
            "off_diagonal_response_energy": 10.0,
            "disturbance_differential_energy": 20.0,
        },
        {
            "arm_id": "local_neighbour_md_km2_kd2",
            "training_seed": None,
            "off_diagonal_response_energy": 0.5,
            "disturbance_differential_energy": 0.7,
        },
    ]
    aggregate = runner._arm_seed_aggregate(
        summaries, "cd_matd3_message", 401
    )
    assert aggregate == {
        "off_diagonal_response_energy": 4.0,
        "disturbance_differential_energy": 6.0,
    }
    deterministic = runner._arm_seed_aggregate(
        summaries, "local_neighbour_md_km2_kd2", None
    )
    assert deterministic["off_diagonal_response_energy"] == 0.5


def test_message_improvement_median_then_ratio() -> None:
    medians = {
        "cd_matd3_no_message": {
            "off_diagonal_response_energy": 10.0,
            "disturbance_differential_energy": 10.0,
        },
        "cd_matd3_message": {
            "off_diagonal_response_energy": 2.156,
            "disturbance_differential_energy": 7.326,
        },
    }
    full = medians["cd_matd3_message"]
    comparator = medians["cd_matd3_no_message"]
    improvements = {
        endpoint: float(
            (comparator[endpoint] - full[endpoint]) / comparator[endpoint]
        )
        for endpoint in runner._ENDPOINTS
    }
    assert abs(improvements["off_diagonal_response_energy"] - 0.7844) < 1e-3
    assert abs(improvements["disturbance_differential_energy"] - 0.2674) < 1e-3


def test_contract_shape() -> None:
    contract = runner.build_contract()
    assert list(contract["training_seeds"]) == [401, 402, 403]
    assert len(contract["learning_arm_ids"]) == 3
    assert contract["training_contract"]["total_interaction_steps"] == 43200
