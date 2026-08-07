"""Public conclusion-seam tests for the R363 common-channel headroom gate."""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.common_channel_qp import (
    FOUR_CHANNEL_COLUMNS,
    build_four_channel_control_response_map,
    solve_common_channel_joint_endpoint_qp,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from probes.r363_common_channel_qp import (
    DEVELOPMENT_CASE_COUNT,
    R358_BASELINE_FEASIBLE_COUNT,
    classify_common_channel_gate,
)


def _identity_cases(count: int) -> list[dict[str, object]]:
    return [
        {
            "scenario_id": f"s{index}",
            "point": "FV0" if index % 2 == 0 else "FV1",
            "channel": f"PQ_{index % 4}",
            "sign": "positive" if index % 2 else "negative",
        }
        for index in range(count)
    ]


def test_four_channel_response_shape_and_causality() -> None:
    from probes.r353_matched_residual_headroom import load_frozen_point_model
    from scripts.run_r353_matched_residual_headroom import (
        POINT_MODEL_DIGESTS,
        R341_CANDIDATE_MODELS,
    )

    payload = __import__("json").load(open("results/r341_staged_fresh_model_validation/candidate_models.json", encoding="utf-8")) if False else None

    from scripts import run_r353_matched_residual_headroom as r353_parent

    raw = r353_parent._read_json(R341_CANDIDATE_MODELS)
    model = load_frozen_point_model(
        raw,
        point="FV0",
        expected_digest=POINT_MODEL_DIGESTS["FV0"],
    )
    response = build_four_channel_control_response_map(model, horizon=25)
    assert response.shape == (4 * 25, FOUR_CHANNEL_COLUMNS * 25)
    assert np.all(np.isfinite(response))
    # causality: output step m must not depend on action step > m
    for output_step in range(5):
        for action_step in range(output_step + 1, 25):
            block = response[
                4 * output_step : 4 * (output_step + 1),
                4 * action_step : 4 * (action_step + 1),
            ]
            assert np.allclose(block, 0.0, atol=1.0e-14)


def test_synthetic_feasible_and_infeasible_decisions() -> None:
    limits = FeedbackLimits()
    feasible_response = np.zeros((4, 4))
    feasible_response[0, 0] = -1.0 / limits.node_ramp
    feasible_response[1, 0] = -1.0 / limits.node_ramp
    feasible_response[2, 0] = 1.0 / limits.node_ramp
    fixed_differential_response = np.zeros((4, 4))
    fixed_differential_response[0, 0] = -1.0 / limits.node_ramp
    common = {
        "base_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "base_node_commands": np.zeros((1, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "minimum_improvement_fraction": 0.02,
        "limits": limits,
    }
    feasible = solve_common_channel_joint_endpoint_qp(
        **common,
        response_map=feasible_response,
    )
    infeasible = solve_common_channel_joint_endpoint_qp(
        **common,
        response_map=fixed_differential_response,
    )
    assert feasible.get("status") == "optimal"
    assert feasible.get("accepted") is True
    assert feasible.get("target_feasible") is True
    assert infeasible.get("status") == "optimal"
    assert infeasible.get("accepted") is True
    assert infeasible.get("target_feasible") is False


def test_classify_common_channel_gate_expanded() -> None:
    cases = _identity_cases(DEVELOPMENT_CASE_COUNT)
    rows = []
    for index, case in enumerate(cases):
        accepted = index < 12
        row = {
            "scenario_id": case["scenario_id"],
            "point": case["point"],
            "channel": case["channel"],
            "sign": case["sign"],
            "status": "optimal",
            "accepted": accepted,
            "target_feasible": accepted,
        }
        rows.append(row)
    decision = classify_common_channel_gate(cases=cases, rows=rows)
    assert decision["classification"] == "COMMON-CHANNEL-HEADROOM-EXPANDED"
    assert decision["feasible_count"] == 12
    assert decision["r358_baseline_feasible_count"] == R358_BASELINE_FEASIBLE_COUNT
    assert decision["headroom_expanded"] is True
    assert decision["training_authorized"] is False


def test_classify_common_channel_gate_unchanged() -> None:
    cases = _identity_cases(DEVELOPMENT_CASE_COUNT)
    rows = []
    for index, case in enumerate(cases):
        accepted = index < 10
        row = {
            "scenario_id": case["scenario_id"],
            "point": case["point"],
            "channel": case["channel"],
            "sign": case["sign"],
            "status": "optimal",
            "accepted": accepted,
            "target_feasible": accepted,
        }
        rows.append(row)
    decision = classify_common_channel_gate(cases=cases, rows=rows)
    assert decision["classification"] == "COMMON-CHANNEL-HEADROOM-UNCHANGED"
    assert decision["feasible_count"] == 10
    assert decision["headroom_expanded"] is False
    assert decision["successor_question_authorized"] is False
    assert decision["training_authorized"] is False


def test_classify_common_channel_gate_invalid() -> None:
    cases = _identity_cases(DEVELOPMENT_CASE_COUNT)
    rows = [
        {
            "scenario_id": case["scenario_id"],
            "status": "unknown",
            "accepted": False,
            "target_feasible": None,
        }
        for case in cases
    ]
    decision = classify_common_channel_gate(cases=cases, rows=rows)
    assert decision["classification"] == "ANALYSIS-INVALID"
    assert "all_solved" in decision["failed_integrity_checks"]


def test_classify_common_channel_gate_rejects_mismatch() -> None:
    cases = _identity_cases(DEVELOPMENT_CASE_COUNT)
    rows = [
        {
            "scenario_id": f"other_{index}",
            "status": "optimal",
            "accepted": True,
            "target_feasible": True,
        }
        for index in range(DEVELOPMENT_CASE_COUNT)
    ]
    with pytest.raises(ValueError):
        classify_common_channel_gate(cases=cases, rows=rows)
