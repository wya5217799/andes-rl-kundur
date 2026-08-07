"""Public-interface tests for the R356 independent feasibility diagnosis."""

from __future__ import annotations

import numpy as np
from probes.r356_joint_endpoint_feasibility import (
    classify_joint_endpoint_feasibility,
    solve_joint_endpoint_feasibility,
)
from scripts import run_r353_matched_residual_headroom as parent_runner

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.residual_headroom import build_control_response_map


def test_uncontrollable_joint_target_has_independent_infeasibility_certificate() -> None:
    """A positive endpoint with zero action response cannot improve by two percent."""

    result = solve_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        response_map=np.zeros((4, 3)),
        minimum_improvement_fraction=0.02,
    )

    assert result["status"] == "primal infeasible"
    assert result["accepted"] is True
    assert result["residual_as_primal_infeasibility_certificate"] <= 1.0e-8


def test_controllable_joint_target_has_accepted_optimal_solution() -> None:
    """One edge that reduces both positive endpoints makes the target feasible."""

    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / FeedbackLimits().node_ramp
    response[1, 0] = -1.0 / FeedbackLimits().node_ramp
    response[2, 0] = 1.0 / FeedbackLimits().node_ramp

    result = solve_joint_endpoint_feasibility(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        response_map=response,
        minimum_improvement_fraction=0.02,
    )

    assert result["status"] == "optimal"
    assert result["accepted"] is True
    assert result["common_ratio"] <= 0.98 + 1.0e-8
    assert result["differential_ratio"] <= 0.98 + 1.0e-8


def test_any_accepted_infeasible_case_blocks_training() -> None:
    result = classify_joint_endpoint_feasibility(
        [
            {"status": "primal infeasible", "accepted": True},
            *[
                {"status": "optimal", "accepted": True}
                for _ in range(15)
            ],
        ]
    )

    assert result["classification"] == "NO-TRAINING"
    assert result["training_authorized"] is False


def test_only_complete_accepted_optimal_bank_allows_classifier_repair() -> None:
    result = classify_joint_endpoint_feasibility(
        [{"status": "optimal", "accepted": True} for _ in range(16)]
    )

    assert result["classification"] == "CLASSIFIER-REPAIR-ELIGIBLE"
    assert result["training_authorized"] is False


def test_unknown_or_unaccepted_solver_result_invalidates_analysis() -> None:
    for rows in (
        [{"status": "unknown", "accepted": False}],
        [{"status": "optimal", "accepted": False}],
        [{"status": "optimal", "accepted": True} for _ in range(15)],
        [],
    ):
        result = classify_joint_endpoint_feasibility(rows)
        assert result["classification"] == "ANALYSIS-INVALID"
        assert result["training_authorized"] is False


def test_frozen_representative_case_is_independently_primal_infeasible() -> None:
    """Replay one R355 failure through the independent public seam."""

    inventory = [
        row
        for row in parent_runner.load_parent_inventory("development")
        if row["scenario_id"] == "development__FV0__PQ_0__negative"
    ]
    assert len(inventory) == 1
    case = parent_runner._build_cases(inventory)[0]
    response = build_control_response_map(
        case["model"], horizon=np.asarray(case["base_outputs"]).shape[0]
    )

    result = solve_joint_endpoint_feasibility(
        base_outputs=np.asarray(case["base_outputs"]),
        response_map=response,
        minimum_improvement_fraction=0.02,
    )

    assert result["status"] == "primal infeasible"
    assert result["accepted"] is True
