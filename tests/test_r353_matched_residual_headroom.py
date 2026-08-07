from __future__ import annotations

import numpy as np
import pytest
from probes.r353_matched_residual_headroom import (
    causal_edge_features,
    classify_residual_gate,
    development_proposals,
    fit_edge_estimators,
    leave_one_scenario_out_proposals,
    pair_primary_records,
    predict_edge_estimators,
    residual_endpoint_gate,
    stage_decision,
    verify_parent_trace_identity,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import SeparateInputRealization
from andes_rl_kundur.control.residual_headroom import (
    build_control_response_map,
    project_edge_sequence_to_headroom,
    solve_three_start_edge_residual,
)


def _record(scenario: str, arm: str, index: int) -> dict[str, object]:
    path = f"results/r352/{scenario}_{arm}.json.gz"
    return {
        "scenario_id": scenario,
        "arm": arm,
        "record_index": index,
        "candidate_id": "kf500_kr0" if arm != "zero_edge" else None,
        "integrity_valid": True,
        "information_action_contract_pass": True,
        "physical_guards_pass": True,
        "trace": {"path": path, "sha256": f"sha-{index}"},
    }


def test_parent_inventory_returns_only_manifest_bound_primary_pairs() -> None:
    records = [
        _record("s0", "zero_edge", 0),
        _record("s0", "selected_local", 1),
        _record("s0", "joint_upper", 2),
        _record("s1", "zero_edge", 3),
        _record("s1", "selected_local", 4),
        _record("s1", "joint_upper", 5),
    ]
    manifest = {str(record["trace"]["path"]): str(record["trace"]["sha256"]) for record in records}

    pairs = pair_primary_records(
        records,
        manifest_entries=manifest,
        expected_scenarios={"s0", "s1"},
        selected_candidate_id="kf500_kr0",
    )

    assert set(pairs) == {"s0", "s1"}
    assert all(set(arms) == {"zero_edge", "selected_local"} for arms in pairs.values())
    assert all(arms["selected_local"]["candidate_id"] == "kf500_kr0" for arms in pairs.values())


def test_parent_inventory_rejects_a_primary_record_that_failed_a_guard() -> None:
    records = [_record("s0", "zero_edge", 0), _record("s0", "selected_local", 1)]
    records[1]["information_action_contract_pass"] = False
    manifest = {str(record["trace"]["path"]): str(record["trace"]["sha256"]) for record in records}

    with pytest.raises(ValueError, match="guard"):
        pair_primary_records(
            records,
            manifest_entries=manifest,
            expected_scenarios={"s0"},
            selected_candidate_id="kf500_kr0",
        )


def test_parent_trace_identity_rejects_record_spec_mismatch() -> None:
    record = _record("development__FV0__PQ_0__positive", "selected_local", 7)
    record.update(
        {
            "round": "R352",
            "question": "Q-0093",
            "point": "FV0",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "source_arm": "local_candidate",
        }
    )
    trace = {
        "round": "R352",
        "question": "Q-0093",
        "spec": {
            "scenario_id": record["scenario_id"],
            "point": "FV0",
            "channel": {"device_idx": "PQ_1"},
            "sign": "positive",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "arm": "local_candidate",
            "candidate_id": "kf500_kr0",
            "record_index": 7,
            "total_steps": 25,
            "waveform": "ramp_hold_unit",
        },
        "rows": [{}] * 25,
    }

    with pytest.raises(ValueError, match="channel"):
        verify_parent_trace_identity(record, trace, bank="development", samples_per_trace=25)


def test_parent_trace_identity_rejects_record_identity_drift() -> None:
    record = _record("development__FV0__PQ_0__positive", "selected_local", 7)
    record.update(
        {
            "round": "wrong",
            "question": "Q-0093",
            "point": "FV0",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "source_arm": "local_candidate",
        }
    )
    trace = {
        "round": "R352",
        "question": "Q-0093",
        "spec": {
            "scenario_id": record["scenario_id"],
            "point": "FV0",
            "channel": {"device_idx": "PQ_0"},
            "sign": "positive",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "arm": "local_candidate",
            "candidate_id": "kf500_kr0",
            "record_index": 7,
            "total_steps": 25,
            "waveform": "ramp_hold_unit",
        },
        "rows": [{}] * 25,
    }

    with pytest.raises(ValueError, match="record identity"):
        verify_parent_trace_identity(record, trace, bank="development", samples_per_trace=25)


def test_parent_trace_identity_rejects_scenario_point_mismatch() -> None:
    record = _record("development__FV0__PQ_0__positive", "selected_local", 7)
    record.update(
        {
            "round": "R352",
            "question": "Q-0093",
            "point": "FV1",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "source_arm": "local_candidate",
        }
    )
    trace = {
        "round": "R352",
        "question": "Q-0093",
        "spec": {
            "scenario_id": record["scenario_id"],
            "point": "FV1",
            "channel": {"device_idx": "PQ_0"},
            "sign": "positive",
            "mode": "development",
            "identity": "DEVELOPMENT",
            "arm": "local_candidate",
            "candidate_id": "kf500_kr0",
            "record_index": 7,
            "total_steps": 25,
            "waveform": "ramp_hold_unit",
        },
        "rows": [{}] * 25,
    }

    with pytest.raises(ValueError, match="scenario point"):
        verify_parent_trace_identity(record, trace, bank="development", samples_per_trace=25)


def test_causal_edge_features_use_only_endpoints_and_past_executed_actions() -> None:
    frequency = np.array(
        [[60.0, 60.1, 59.7, 61.0], [60.2, 60.0, 59.6, 62.0], [60.4, 59.8, 59.5, 63.0]]
    )
    edge_flow = np.array([[1.0, 8.0, 9.0], [2.0, 18.0, 19.0], [3.0, 28.0, 29.0]])
    achieved = np.arange(12, dtype=float).reshape(3, 4)
    commanded = achieved + 20.0
    soc = achieved + 40.0
    voltage = achieved + 60.0

    features = causal_edge_features(
        frequency_hz_before_action=frequency,
        executed_edge_flows_after_action=edge_flow,
        achieved_node_power_after_action=achieved,
        commanded_node_power_after_action=commanded,
        soc_before_action=soc,
        voltage_before_action=voltage,
        edge=(0, 1),
        edge_index=0,
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
    )

    assert features.shape == (3, 13)
    np.testing.assert_allclose(
        features[1],
        [0.2, 0.0, 1.0, -0.5, 1.0, 0.0, 1.0, 20.0, 21.0, 44.0, 45.0, 64.0, 65.0],
    )

    frequency[:, 3] += 1000.0
    achieved[:, 3] += 1000.0
    commanded[:, 3] += 1000.0
    edge_flow[2, 0] += 1000.0
    changed = causal_edge_features(
        frequency_hz_before_action=frequency,
        executed_edge_flows_after_action=edge_flow,
        achieved_node_power_after_action=achieved,
        commanded_node_power_after_action=commanded,
        soc_before_action=soc,
        voltage_before_action=voltage,
        edge=(0, 1),
        edge_index=0,
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
    )
    np.testing.assert_allclose(changed[:2], features[:2])


def test_development_fit_produces_frozen_edge_models_for_unlabelled_holdout() -> None:
    identity = np.eye(13)
    development_matrix = np.vstack((identity, -identity, np.zeros((1, 13))))
    coefficients = np.vstack(
        (
            np.arange(1.0, 14.0),
            np.arange(2.0, 15.0),
            np.arange(3.0, 16.0),
        )
    ).T
    development_targets = 0.25 + development_matrix @ coefficients
    development_features = {
        "s0": tuple(development_matrix[:14].copy() for _ in range(3)),
        "s1": tuple(development_matrix[14:].copy() for _ in range(3)),
    }
    targets = {
        "s0": development_targets[:14],
        "s1": development_targets[14:],
    }

    models = fit_edge_estimators(development_features, targets)
    holdout = 0.5 * identity[:3]
    predictions = predict_edge_estimators(models, tuple(holdout.copy() for _ in range(3)))

    np.testing.assert_allclose(predictions, 0.25 + holdout @ coefficients, atol=1e-12)


def test_gate_decision_never_authorizes_training() -> None:
    eligible = classify_residual_gate(
        integrity_checks={"parent_closure": True},
        scientific_checks={"local_nominal": True, "local_mismatch": True},
    )
    negative = classify_residual_gate(
        integrity_checks={"parent_closure": True},
        scientific_checks={"local_nominal": True, "local_mismatch": False},
    )
    invalid = classify_residual_gate(
        integrity_checks={"parent_closure": False},
        scientific_checks={"local_nominal": True, "local_mismatch": True},
    )

    assert eligible["conclusion"] == "RESIDUAL-PROBE-ELIGIBLE"
    assert negative["conclusion"] == "NO-TRAINING"
    assert invalid["conclusion"] == "ANALYSIS-INVALID"
    assert not eligible["training_authorized"]
    assert not negative["training_authorized"]
    assert not invalid["training_authorized"]


def test_stage_decision_treats_certificate_failure_as_invalid_before_endpoints() -> None:
    decision = stage_decision(
        cases=[{"scenario_id": "s0", "point": "p0", "channel": "c0", "sign": "pos"}],
        oracle=[
            {
                "scenario_id": "s0",
                "optimizer_valid": False,
                "certified_start_count": 0,
            }
        ],
        local=[],
        model_adequacy=None,
        include_mismatch=False,
        minimum_improvement_fraction=0.02,
        confidence_level=0.95,
        maximum_single_scenario_ratio=1.05,
    )

    assert decision["conclusion"] == "ANALYSIS-INVALID"
    assert "oracle_certificates" in decision["failed_integrity_checks"]
    assert not decision["training_authorized"]


def test_endpoint_gate_rejects_one_scenario_above_the_frozen_ratio_limit() -> None:
    baseline = np.ones(16)
    candidate = np.array([0.8] * 15 + [1.06])

    gate = residual_endpoint_gate(
        baseline,
        candidate,
        groups={"point": ["p0"] * 16},
        minimum_improvement_fraction=0.02,
        confidence_level=0.95,
        maximum_single_scenario_ratio=1.05,
    )

    assert gate["paired_gate"]["pass"]
    assert gate["maximum_observed_ratio"] == pytest.approx(1.06)
    assert not gate["pass"]


def test_leave_one_out_prediction_cannot_use_its_own_oracle_target() -> None:
    basis = np.vstack((np.eye(13), -np.eye(13), np.zeros((1, 13))))
    features = {
        scenario: tuple((basis + offset).copy() for _ in range(3))
        for scenario, offset in (("s0", 0.0), ("s1", 0.1), ("s2", -0.1))
    }
    targets = {
        scenario: np.column_stack(
            (
                matrix[:, 0] + 0.1,
                matrix[:, 1] + 0.2,
                matrix[:, 2] + 0.3,
            )
        )
        for scenario, matrix in (
            (scenario, edge_features[0]) for scenario, edge_features in features.items()
        )
    }

    original = leave_one_scenario_out_proposals(features, targets)
    changed_targets = {name: values.copy() for name, values in targets.items()}
    changed_targets["s0"] += 10_000.0
    changed = leave_one_scenario_out_proposals(features, changed_targets)

    np.testing.assert_allclose(changed["s0"], original["s0"], atol=1e-12)


def test_development_proposals_zero_two_unrecoverable_startup_samples() -> None:
    basis = np.vstack((np.eye(13), -np.eye(13), np.zeros((1, 13))))
    cases = [
        {
            "scenario_id": scenario,
            "features": tuple((basis + offset).copy() for _ in range(3)),
        }
        for scenario, offset in (("s0", 0.0), ("s1", 0.1), ("s2", -0.1))
    ]
    oracle = [
        {
            "scenario_id": case["scenario_id"],
            "edge_actions": np.column_stack(
                (
                    case["features"][0][:, 0] + 0.1,
                    case["features"][1][:, 1] + 0.2,
                    case["features"][2][:, 2] + 0.3,
                )
            ).tolist(),
        }
        for case in cases
    ]

    proposals = development_proposals(cases, oracle, startup_samples=2)

    assert len(proposals) == 3
    for proposal in proposals:
        np.testing.assert_array_equal(proposal[:2], np.zeros((2, 3)))
        assert np.any(proposal[2:] != 0.0)


def test_promoted_three_start_and_projection_preserve_frozen_physics() -> None:
    direct = np.zeros((4, 4))
    direct[:, 1] = np.asarray([-1.0, -1.0, 0.0, 0.0])
    model = SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    settings = {
        "limits": FeedbackLimits(),
        "maximum_iterations": 20_000,
        "function_tolerance": 1.0e-9,
        "feasibility_tolerance": 1.0e-8,
    }
    solved = solve_three_start_edge_residual(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=build_control_response_map(model, horizon=1),
        minimum_improvement_fraction=0.02,
        **settings,
    )

    assert tuple(start.name for start in solved.starts) == ("feasibility", "zero", "r348")
    assert solved.selected is not None
    assert solved.selected.certificate.valid
    np.testing.assert_allclose(
        solved.selected.edge_actions,
        np.asarray([[0.02, 0.0, 0.0]]),
        rtol=0.0,
        atol=1.0e-6,
    )

    projected = project_edge_sequence_to_headroom(
        proposed_edge_actions=np.full((4, 3), 1.0),
        base_node_commands=np.zeros((4, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        **settings,
    )
    assert projected.feasible
    np.testing.assert_allclose(
        np.sum(projected.residual_node_actions, axis=1),
        0.0,
        rtol=0.0,
        atol=1.0e-12,
    )
