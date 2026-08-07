"""Public-interface tests for the R357 exact physical feasibility seam."""

from __future__ import annotations

import numpy as np
import pytest

from probes.r357_physical_joint_endpoint_feasibility import (
    classify_physical_joint_endpoint_feasibility,
    solve_physical_joint_endpoint_feasibility,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits


def test_controllable_target_within_physical_limits_has_accepted_witness() -> None:
    """A small one-edge correction can satisfy both targets and every limit."""

    limits = FeedbackLimits()
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp
    response[1, 0] = -1.0 / limits.node_ramp
    response[2, 0] = 1.0 / limits.node_ramp

    result = solve_physical_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=response,
        minimum_improvement_fraction=0.02,
        limits=limits,
    )

    assert result["status"] == "optimal"
    assert result["accepted"] is True
    assert result["physical_constraints_included"] is True
    assert result["soc_redundancy_proved"] is True
    assert result["common_ratio"] <= 0.98 + 1.0e-8
    assert result["differential_ratio"] <= 0.98 + 1.0e-8
    assert result["maximum_power_violation"] <= 1.0e-8
    assert result["maximum_ramp_violation"] <= 1.0e-8
    assert result["maximum_soc_violation"] <= 1.0e-8


def test_relaxed_target_becomes_certifiably_infeasible_at_power_limit() -> None:
    """The only useful edge direction is blocked when its source is saturated."""

    limits = FeedbackLimits()
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp
    response[1, 0] = -1.0 / limits.node_ramp
    response[2, 0] = 1.0 / limits.node_ramp
    commands = np.asarray([[limits.node_power, 0.0, 0.0, 0.0]])

    result = solve_physical_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=commands,
        previous_node_command=commands[0],
        initial_soc=np.full(4, 0.5),
        response_map=response,
        minimum_improvement_fraction=0.02,
        limits=limits,
    )

    assert result["status"] == "primal infeasible"
    assert result["accepted"] is True
    assert result["residual_as_primal_infeasibility_certificate"] <= 1.0e-8


def test_uncontrollable_endpoint_has_accepted_infeasibility_certificate() -> None:
    result = solve_physical_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=np.zeros((4, 3)),
        minimum_improvement_fraction=0.02,
    )

    assert result["status"] == "primal infeasible"
    assert result["accepted"] is True


def test_unproved_soc_redundancy_fails_before_solver() -> None:
    limits = FeedbackLimits()

    with pytest.raises(ValueError, match="state-of-charge redundancy"):
        solve_physical_joint_endpoint_feasibility(
            base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
            base_node_commands=np.zeros((1, 4)),
            previous_node_command=np.zeros(4),
            initial_soc=np.full(4, limits.minimum_soc),
            response_map=np.zeros((4, 3)),
            minimum_improvement_fraction=0.02,
            limits=limits,
        )


def test_complete_bank_with_one_witness_finds_physical_headroom() -> None:
    decision = classify_physical_joint_endpoint_feasibility(
        [
            {"status": "optimal", "accepted": True},
            *[
                {"status": "primal infeasible", "accepted": True}
                for _ in range(15)
            ],
        ]
    )

    assert decision["classification"] == "PHYSICAL-HEADROOM-FOUND"
    assert decision["accepted_optimal_count"] == 1
    assert decision["training_authorized"] is False


def test_incomplete_or_unaccepted_bank_is_invalid() -> None:
    for rows in (
        [{"status": "optimal", "accepted": True} for _ in range(15)],
        [
            {"status": "optimal", "accepted": False},
            *[{"status": "primal infeasible", "accepted": True} for _ in range(15)],
        ],
        [{"status": "unknown", "accepted": True} for _ in range(16)],
    ):
        decision = classify_physical_joint_endpoint_feasibility(rows)
        assert decision["classification"] == "ANALYSIS-INVALID"
        assert decision["training_authorized"] is False
