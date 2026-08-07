"""Contract tests for the create-only R345 residual-headroom analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import scripts.run_r345_residual_headroom as adapter
from probes.r345_residual_headroom import (
    apply_standardized_ols,
    build_control_response_map,
    causal_edge_features,
    endpoint_values,
    fit_standardized_ols,
    paired_endpoint_gate,
    physical_frequency_from_coordinates,
    project_edge_sequence_to_headroom,
    solve_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputRealization,
)
from andes_rl_kundur.env.andes.model_first_contract import (
    weighted_common_differential_transform,
)


def test_contract_freezes_create_only_parallel_analysis_and_learning_exclusions() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R345"
    assert contract["question"] == "Q-0091"
    assert contract["inventory"] == {
        "scenario_pairs": 16,
        "records": 32,
        "samples_per_trace": 25,
        "operating_points": 2,
        "disturbance_locations": 4,
        "signs": 2,
    }
    assert contract["execution"]["worker_processes"] == 16
    assert contract["execution"]["native_threads_per_process"] == 1
    assert contract["execution"]["create_only"] is True
    assert contract["decision"]["training_authorized"] is False
    assert contract["decision"]["distributed_runtime_authorized"] is False
    assert contract["decision"]["eval_authorized"] is False
    assert not any(contract["exclusions"].values())


def test_parser_exposes_only_prepare_and_analyse_without_training_or_eval() -> None:
    parser = adapter.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")

    assert set(subparsers.choices) == {"prepare", "analyse"}
    assert not {"train", "training", "eval", "distributed"} & set(subparsers.choices)


def test_prepare_is_create_only_and_binds_the_frozen_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("state: active\nQ-0091\n", encoding="utf-8")
    seal = tmp_path / "analysis_seal.json"
    result_root = tmp_path / "result"
    sources = {"adapter": {"path": "adapter.py", "sha256": "a" * 64}}
    monkeypatch.setattr(adapter, "PLAN", plan)
    monkeypatch.setattr(adapter, "DEFAULT_OUT", result_root)
    monkeypatch.setattr(adapter, "_verify_expected_inputs", lambda: None)
    monkeypatch.setattr(adapter, "_seal_sources", lambda: sources)

    digest = adapter.prepare(seal)
    payload, verified = adapter.load_seal(seal, digest)

    assert verified == digest
    assert payload["contract"] == adapter.build_contract()
    assert payload["sources"] == sources
    assert payload["result_root_absent_at_freeze"] is True
    assert payload["formal_retry_authorized"] is False
    with pytest.raises(FileExistsError, match="seal already exists"):
        adapter.prepare(seal)


def _cross_coupled_model() -> SeparateInputRealization:
    direct = np.zeros((4, 4))
    direct[0, 1:] = 0.25
    direct[1:, 1:] = np.eye(3)
    return SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )


def test_logged_causal_coordinates_recover_endpoint_physical_frequencies() -> None:
    inertia = np.asarray([4.0, 9.0, 16.0, 25.0])
    coordinates = np.asarray([[0.01, -0.02, 0.03, -0.04], [-0.05, 0.06, -0.07, 0.08]])
    reference = np.asarray([60.0, 60.0, 60.0, 60.0])
    transform = weighted_common_differential_transform(inertia)
    expected = reference + 60.0 * (transform.inverse @ coordinates.T).T

    actual = physical_frequency_from_coordinates(
        coordinates,
        reference_frequency_hz=reference,
        inertia_system=inertia,
    )

    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-12)


def test_control_response_uses_only_three_edge_coordinates() -> None:
    model = _cross_coupled_model()

    response = build_control_response_map(model, horizon=3)
    actions = np.asarray([[0.01, -0.02, 0.03], [0.04, 0.05, -0.06], [0.0, 0.0, 0.0]])

    actual = (response @ actions.reshape(-1)).reshape(3, 4)
    expected = np.vstack([model.control_feedthrough_matrix[:, 1:] @ row for row in actions])
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1.0e-12)


def test_minimum_norm_oracle_meets_both_endpoints_and_physical_limits() -> None:
    horizon = 5
    model = _cross_coupled_model()
    base = np.tile(np.asarray([0.02, 0.03, -0.02, 0.01]), (horizon, 1))
    commands = np.zeros((horizon, 4))
    previous = np.zeros(4)
    limits = FeedbackLimits()

    result = solve_minimum_norm_edge_residual(
        base_outputs=base,
        base_node_commands=commands,
        previous_node_command=previous,
        initial_soc=np.full(4, 0.5),
        response_map=build_control_response_map(model, horizon=horizon),
        limits=limits,
        minimum_improvement_fraction=0.02,
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )

    assert result.feasible, result.message
    assert result.optimizer_valid
    assert result.target_feasible
    base_endpoints = endpoint_values(base, sample_period_seconds=0.2)
    candidate_endpoints = endpoint_values(
        result.counterfactual_outputs,
        sample_period_seconds=0.2,
    )
    assert candidate_endpoints["common_coordinate_iae"] <= (
        0.98 * base_endpoints["common_coordinate_iae"] + 1.0e-8
    )
    assert candidate_endpoints["differential_coordinate_energy"] <= (
        0.98 * base_endpoints["differential_coordinate_energy"] + 1.0e-8
    )
    assert result.maximum_constraint_residual <= 1.0e-8
    np.testing.assert_allclose(
        np.sum(result.residual_node_actions, axis=1),
        0.0,
        rtol=0.0,
        atol=1.0e-12,
    )


def test_valid_oracle_separates_unreachable_target_from_optimizer_failure() -> None:
    horizon = 5
    model = SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=np.zeros((4, 4)),
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    base = np.tile(np.asarray([0.02, 0.03, -0.02, 0.01]), (horizon, 1))

    result = solve_minimum_norm_edge_residual(
        base_outputs=base,
        base_node_commands=np.zeros((horizon, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=build_control_response_map(model, horizon=horizon),
        limits=FeedbackLimits(),
        minimum_improvement_fraction=0.02,
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )

    assert result.optimizer_valid
    assert not result.target_feasible
    assert not result.feasible
    assert result.maximum_target_shortfall > 0.0


def test_causal_features_contain_only_edge_endpoint_values() -> None:
    frequency = np.asarray([[60.1, 60.2, 60.3, 60.4], [59.9, 59.8, 59.7, 59.6]])
    achieved = np.asarray([[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]])
    commanded = achieved + 10.0

    features = causal_edge_features(
        frequency_hz_before_action=frequency,
        achieved_node_power_before_action=achieved,
        commanded_node_power_before_action=commanded,
        edge=(1, 2),
        nominal_frequency_hz=60.0,
    )

    expected = np.column_stack(
        (
            frequency[:, 1] - 60.0,
            frequency[:, 2] - 60.0,
            achieved[:, 1],
            achieved[:, 2],
            commanded[:, 1],
            commanded[:, 2],
        )
    )
    np.testing.assert_allclose(features, expected, rtol=0.0, atol=1.0e-12)


def test_standardized_ols_reconstructs_an_exact_causal_mapping() -> None:
    features = np.asarray([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, -1.0]])
    target = 0.3 + 2.0 * features[:, 0] - 0.5 * features[:, 1]

    model = fit_standardized_ols(features, target)
    predicted = apply_standardized_ols(model, features)

    np.testing.assert_allclose(predicted, target, rtol=0.0, atol=1.0e-12)


def test_predicted_edge_sequence_is_projected_to_fleet_neutral_headroom() -> None:
    horizon = 4
    proposed = np.full((horizon, 3), 1.0)
    base_commands = np.zeros((horizon, 4))

    projected = project_edge_sequence_to_headroom(
        proposed_edge_actions=proposed,
        base_node_commands=base_commands,
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        limits=FeedbackLimits(),
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )

    assert projected.feasible, projected.message
    assert projected.maximum_constraint_residual <= 1.0e-8
    np.testing.assert_allclose(
        np.sum(projected.residual_node_actions, axis=1),
        0.0,
        rtol=0.0,
        atol=1.0e-12,
    )
    assert np.max(np.abs(projected.counterfactual_node_commands)) <= (
        FeedbackLimits().node_power + 1.0e-8
    )


def test_paired_gate_requires_material_mean_confidence_and_every_subgroup() -> None:
    changes = np.asarray([-0.03, -0.04, -0.05, -0.06] * 4)
    groups = {
        "point": ["p0"] * 8 + ["p1"] * 8,
        "channel": ["c0", "c1", "c2", "c3"] * 4,
        "sign": ["pos", "neg"] * 8,
    }

    passing = paired_endpoint_gate(
        changes,
        groups=groups,
        minimum_improvement_fraction=0.02,
        confidence_level=0.95,
    )
    failing = paired_endpoint_gate(
        np.asarray([-0.03] * 15 + [0.50]),
        groups=groups,
        minimum_improvement_fraction=0.02,
        confidence_level=0.95,
    )

    assert passing["pass"] is True
    assert passing["mean_improvement_fraction"] >= 0.02
    assert passing["one_sided_upper_bound"] < 0.0
    assert failing["pass"] is False
