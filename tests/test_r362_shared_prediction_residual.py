"""Public conclusion-seam tests for the R362 shared-prediction gate."""

from __future__ import annotations

import numpy as np
import pytest
from probes.r362_shared_prediction_residual import (
    SHARED_PREDICTION_FAMILY,
    classify_shared_prediction_gate,
    leave_one_scenario_out_family_proposals,
    predict_holdout_with_frozen_family,
)

from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_message_residual import (
    ONE_HOP_NEIGHBOUR_MESSAGES,
)
from andes_rl_kundur.control.shared_prediction_residual import (
    PREDICTION_STEPS,
    SHARED_PREDICTION_OBSERVATION_DIMENSION,
    SharedPredictionMessage,
    SharedPredictionObservation,
    shared_prediction_observation_vector,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES


def _endpoint(node: int, seed: int, step: int) -> EndpointObservation:
    rng = np.random.default_rng(seed * 1000 + step + node * 17)
    return EndpointObservation(
        node_id=node,
        frequency_deviation_hz=float(rng.normal(0.0, 0.05)),
        rocof_hz_s=float(rng.normal(0.0, 0.1)),
        previous_command_system_pu=float(rng.uniform(-0.05, 0.05)),
        soc=float(rng.uniform(0.2, 0.8)),
        voltage_pu=float(rng.uniform(0.95, 1.05)),
        lower_residual_power_system_pu=float(rng.uniform(-0.05, 0.0)),
        upper_residual_power_system_pu=float(rng.uniform(0.0, 0.05)),
    )


def _observation(edge: tuple[int, int], seed: int, step: int) -> LocalEdgeObservation:
    rng = np.random.default_rng(seed * 1000 + step)
    return LocalEdgeObservation(
        edge=edge,
        source=_endpoint(edge[0], seed, step),
        target=_endpoint(edge[1], seed, step),
        previous_edge_flow_system_pu=float(rng.uniform(-0.05, 0.05)),
    )


def _prediction(node: int, seed: int, step: int) -> SharedPredictionMessage:
    rng = np.random.default_rng(seed * 1000 + step + node * 29)
    return SharedPredictionMessage(
        node_id=node,
        values_hz=np.asarray(rng.normal(0.0, 0.05, PREDICTION_STEPS), dtype=float),
    )


def _shared_prediction(edge: tuple[int, int], seed: int, step: int):
    source_id, target_id = ONE_HOP_NEIGHBOUR_MESSAGES[edge]
    return SharedPredictionObservation(
        edge=edge,
        observation=_observation(edge, seed, step),
        source_neighbour_prediction=_prediction(source_id, seed, step),
        target_neighbour_prediction=_prediction(target_id, seed, step),
    )


def _scenarios(count: int, steps: int, startup: int) -> dict[str, dict[tuple[int, int], tuple]]:
    rows_per_edge = steps - startup
    scenarios: dict[str, dict[tuple[int, int], tuple]] = {}
    for scenario in range(count):
        rows = {
            edge: tuple(_shared_prediction(edge, scenario, step) for step in range(rows_per_edge))
            for edge in ACTION_EDGES
        }
        scenarios[f"s{scenario}"] = rows
    return scenarios


def _targets(count: int, steps: int, startup: int) -> dict[str, np.ndarray]:
    targets: dict[str, np.ndarray] = {}
    for scenario in range(count):
        target = np.zeros((steps, 3), dtype=float)
        phase = float(scenario) / max(count - 1, 1)
        for edge_index in range(3):
            target[startup:, edge_index] = (
                0.25 * np.sin(0.5 * np.arange(steps - startup) + phase + edge_index)
            )
        targets[f"s{scenario}"] = target
    return targets


def test_family_contains_exactly_four_frozen_members() -> None:
    assert set(SHARED_PREDICTION_FAMILY) == {
        "affine",
        "rbf_kernel_ridge",
        "knn",
        "quadratic_polynomial",
    }


def test_shared_prediction_vector_dimension() -> None:
    item = _shared_prediction(ACTION_EDGES[1], 0, 0)
    vector = shared_prediction_observation_vector(item)
    assert vector.shape == (SHARED_PREDICTION_OBSERVATION_DIMENSION,)
    assert SHARED_PREDICTION_OBSERVATION_DIMENSION == 23
    assert np.all(np.isfinite(vector))


def test_one_hop_neighbour_table_matches_communication_ring() -> None:
    ring = {tuple(sorted(edge)) for edge in ((0, 1), (1, 2), (2, 3), (0, 3))}
    for edge, (source_neighbour, target_neighbour) in ONE_HOP_NEIGHBOUR_MESSAGES.items():
        assert edge in {tuple(int(value) for value in item) for item in ACTION_EDGES}
        assert tuple(sorted((edge[0], source_neighbour))) in ring
        assert tuple(sorted((edge[1], target_neighbour))) in ring
        assert source_neighbour != edge[1] and target_neighbour != edge[0]


def test_leave_one_scenario_out_family_proposals_shape_and_startup() -> None:
    scenarios = _scenarios(16, 30, 2)
    targets = _targets(16, 30, 2)
    proposals = leave_one_scenario_out_family_proposals(
        observations_by_scenario=scenarios,
        normalized_targets_by_scenario=targets,
        horizon=30,
        startup_zero_steps=2,
    )
    assert set(proposals) == set(SHARED_PREDICTION_FAMILY)
    for family, rows in proposals.items():
        assert set(rows) == set(targets)
        for proposal in rows.values():
            assert proposal.shape == (30, 3)
            assert np.all(np.isfinite(proposal))
            assert np.array_equal(proposal[:2], np.zeros((2, 3)))
            assert np.all(np.abs(proposal) <= 1.0 + 1.0e-9)


def test_predict_holdout_with_frozen_family() -> None:
    scenarios = _scenarios(16, 30, 2)
    targets = _targets(16, 30, 2)
    trained = leave_one_scenario_out_family_proposals(
        observations_by_scenario=scenarios,
        normalized_targets_by_scenario=targets,
        horizon=30,
        startup_zero_steps=2,
    )
    from probes.r362_shared_prediction_residual import _fit_family

    controllers = _fit_family(
        training_scenario_ids=tuple(sorted(scenarios)),
        observations_by_scenario=scenarios,
        normalized_targets_by_scenario=targets,
        horizon=30,
        startup_zero_steps=2,
    )["knn"]
    proposal = predict_holdout_with_frozen_family(
        controllers=controllers,
        observations=scenarios["s0"],
        horizon=30,
        startup_zero_steps=2,
    )
    assert proposal.shape == (30, 3)
    assert np.array_equal(proposal[:2], np.zeros((2, 3)))
    assert np.all(np.isfinite(proposal))


def test_classify_shared_prediction_gate_or_semantics() -> None:
    integrity = {
        "complete_inventory": True,
        "exact_information": True,
        "neighbour_table_frozen": True,
        "prediction_horizon_frozen": True,
        "startup_mask": True,
        "physical_projection": True,
    }
    all_pass = {
        name: {"nominal_endpoints": True, "mismatch_bounded_endpoints": True}
        for name in SHARED_PREDICTION_FAMILY
    }
    found = classify_shared_prediction_gate(
        integrity_checks=integrity, family_scientific_checks=all_pass
    )
    assert found["classification"] == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
    assert sorted(found["passing_families"]) == sorted(SHARED_PREDICTION_FAMILY)
    assert found["successor_question_authorized"] is True
    assert found["training_authorized"] is False

    one_pass = {
        "affine": {"nominal_endpoints": True, "mismatch_bounded_endpoints": True},
        "rbf_kernel_ridge": {"nominal_endpoints": False, "mismatch_bounded_endpoints": False},
        "knn": {"nominal_endpoints": True, "mismatch_bounded_endpoints": False},
        "quadratic_polynomial": {"nominal_endpoints": False, "mismatch_bounded_endpoints": True},
    }
    found_one = classify_shared_prediction_gate(
        integrity_checks=integrity, family_scientific_checks=one_pass
    )
    assert found_one["classification"] == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
    assert found_one["passing_families"] == ["affine"]

    all_fail = {
        name: {"nominal_endpoints": False, "mismatch_bounded_endpoints": True}
        for name in SHARED_PREDICTION_FAMILY
    }
    stop = classify_shared_prediction_gate(
        integrity_checks=integrity, family_scientific_checks=all_fail
    )
    assert stop["classification"] == "NO-NEIGHBOUR-LEARNABLE-STRUCTURE"
    assert stop["passing_families"] == []
    assert stop["successor_question_authorized"] is False

    invalid = classify_shared_prediction_gate(
        integrity_checks={"complete_inventory": False},
        family_scientific_checks=all_pass,
    )
    assert invalid["classification"] == "ANALYSIS-INVALID"


def test_classify_shared_prediction_gate_rejects_unknown_family() -> None:
    with pytest.raises(ValueError):
        classify_shared_prediction_gate(
            integrity_checks={"complete_inventory": True},
            family_scientific_checks={"unknown_family": {"nominal_endpoints": True}},
        )
