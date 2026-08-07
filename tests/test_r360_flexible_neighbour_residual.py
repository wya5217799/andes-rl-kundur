"""Public conclusion-seam tests for the R360 flexible residual gate."""

from __future__ import annotations

import numpy as np
import pytest
from probes.r360_flexible_neighbour_residual import (
    classify_flexible_gate,
    leave_one_scenario_out_family_proposals,
    predict_holdout_with_frozen_family,
)

from andes_rl_kundur.control.flexible_neighbour_residual import (
    FLEXIBLE_CONTROLLER_FAMILY,
    RBF_REGULARIZATION,
    fit_knn_edge_controller,
    fit_quadratic_polynomial_edge_controller,
    fit_rbf_kernel_ridge_edge_controller,
)
from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.env.andes.model_first_contract import ACTION_EDGES


def _observation(edge: tuple[int, int], seed: int, step: int) -> LocalEdgeObservation:
    rng = np.random.default_rng(seed * 1000 + step)
    def endpoint(node: int) -> EndpointObservation:
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
    return LocalEdgeObservation(
        edge=edge,
        source=endpoint(edge[0]),
        target=endpoint(edge[1]),
        previous_edge_flow_system_pu=float(rng.uniform(-0.05, 0.05)),
    )


def _scenarios(count: int, steps: int, startup: int) -> dict[str, dict[tuple[int, int], tuple]]:
    rows_per_edge = steps - startup
    scenarios: dict[str, dict[tuple[int, int], tuple]] = {}
    for scenario in range(count):
        rows = {
            edge: tuple(_observation(edge, scenario, step) for step in range(rows_per_edge))
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


def test_family_contains_exactly_three_frozen_members() -> None:
    assert set(FLEXIBLE_CONTROLLER_FAMILY) == {
        "rbf_kernel_ridge",
        "knn",
        "quadratic_polynomial",
    }


def test_rbf_kernel_ridge_act_bounded() -> None:
    edge = ACTION_EDGES[0]
    observations = [_observation(edge, seed, step) for seed in range(3) for step in range(4)]
    actions = [0.1 * (seed + 1) for seed in range(3) for _ in range(4)]
    controller = fit_rbf_kernel_ridge_edge_controller(
        edge=edge,
        observations=observations,
        normalized_actions=actions,
    )
    assert controller.regularization == RBF_REGULARIZATION
    assert np.isfinite(controller.width) and controller.width > 0.0
    for row in observations:
        assert -1.0 <= controller.act(row) <= 1.0


def test_knn_act_bounded() -> None:
    edge = ACTION_EDGES[1]
    observations = [_observation(edge, seed, step) for seed in range(3) for step in range(4)]
    actions = [0.2 * (seed - 1) for seed in range(3) for _ in range(4)]
    controller = fit_knn_edge_controller(
        edge=edge,
        observations=observations,
        normalized_actions=actions,
    )
    assert controller.neighbour_count == 5
    for row in observations:
        assert -1.0 <= controller.act(row) <= 1.0


def test_quadratic_polynomial_act_bounded() -> None:
    edge = ACTION_EDGES[2]
    observations = [_observation(edge, seed, step) for seed in range(40) for step in range(4)]
    actions = [0.15 * (seed % 2 - 0.5) for seed in range(40) for _ in range(4)]
    controller = fit_quadratic_polynomial_edge_controller(
        edge=edge,
        observations=observations,
        normalized_actions=actions,
    )
    assert controller.coefficients.shape[0] > 15
    for row in observations[:8]:
        assert -1.0 <= controller.act(row) <= 1.0


def test_leave_one_scenario_out_family_proposals_shape_and_startup() -> None:
    scenarios = _scenarios(16, 12, 2)
    targets = _targets(16, 12, 2)
    proposals = leave_one_scenario_out_family_proposals(
        observations_by_scenario=scenarios,
        normalized_targets_by_scenario=targets,
        horizon=12,
        startup_zero_steps=2,
    )
    assert set(proposals) == set(FLEXIBLE_CONTROLLER_FAMILY)
    for family, rows in proposals.items():
        assert set(rows) == set(targets)
        for proposal in rows.values():
            assert proposal.shape == (12, 3)
            assert np.all(np.isfinite(proposal))
            assert np.array_equal(proposal[:2], np.zeros((2, 3)))
            assert np.all(np.abs(proposal) <= 1.0 + 1.0e-9)


def test_predict_holdout_with_frozen_family() -> None:
    scenarios = _scenarios(16, 12, 2)
    targets = _targets(16, 12, 2)
    trained = leave_one_scenario_out_family_proposals(
        observations_by_scenario=scenarios,
        normalized_targets_by_scenario=targets,
        horizon=12,
        startup_zero_steps=2,
    )
    fitter = FLEXIBLE_CONTROLLER_FAMILY["knn"]
    controllers: dict[tuple[int, int], object] = {}
    for edge_index, edge in enumerate(ACTION_EDGES):
        observations = [
            row
            for scenario in sorted(scenarios)
            for row in scenarios[scenario][edge]
        ]
        actions = [
            value
            for scenario in sorted(targets)
            for value in targets[scenario][2:, edge_index].tolist()
        ]
        controllers[edge] = fitter(
            edge=edge,
            observations=observations,
            normalized_actions=actions,
        )
    proposal = predict_holdout_with_frozen_family(
        controllers=controllers,
        observations=scenarios["s0"],
        horizon=12,
        startup_zero_steps=2,
    )
    assert proposal.shape == (12, 3)
    assert np.array_equal(proposal[:2], np.zeros((2, 3)))
    assert np.all(np.isfinite(proposal))


def test_classify_flexible_gate_or_semantics() -> None:
    integrity = {
        "complete_inventory": True,
        "exact_information": True,
        "startup_mask": True,
        "physical_projection": True,
    }
    all_pass = {
        name: {"nominal_endpoints": True, "mismatch_bounded_endpoints": True}
        for name in FLEXIBLE_CONTROLLER_FAMILY
    }
    found = classify_flexible_gate(integrity_checks=integrity, family_scientific_checks=all_pass)
    assert found["classification"] == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
    assert sorted(found["passing_families"]) == sorted(FLEXIBLE_CONTROLLER_FAMILY)
    assert found["successor_question_authorized"] is True
    assert found["training_authorized"] is False

    one_pass = {
        "rbf_kernel_ridge": {"nominal_endpoints": True, "mismatch_bounded_endpoints": True},
        "knn": {"nominal_endpoints": False, "mismatch_bounded_endpoints": False},
        "quadratic_polynomial": {"nominal_endpoints": True, "mismatch_bounded_endpoints": False},
    }
    found_one = classify_flexible_gate(integrity_checks=integrity, family_scientific_checks=one_pass)
    assert found_one["classification"] == "NEIGHBOUR-LEARNABLE-STRUCTURE-FOUND"
    assert found_one["passing_families"] == ["rbf_kernel_ridge"]

    all_fail = {
        name: {"nominal_endpoints": False, "mismatch_bounded_endpoints": True}
        for name in FLEXIBLE_CONTROLLER_FAMILY
    }
    stop = classify_flexible_gate(integrity_checks=integrity, family_scientific_checks=all_fail)
    assert stop["classification"] == "NO-NEIGHBOUR-LEARNABLE-STRUCTURE"
    assert stop["passing_families"] == []
    assert stop["successor_question_authorized"] is False

    invalid = classify_flexible_gate(
        integrity_checks={"complete_inventory": False},
        family_scientific_checks=all_pass,
    )
    assert invalid["classification"] == "ANALYSIS-INVALID"


def test_classify_flexible_gate_rejects_unknown_family() -> None:
    with pytest.raises(ValueError):
        classify_flexible_gate(
            integrity_checks={"complete_inventory": True},
            family_scientific_checks={"unknown_family": {"nominal_endpoints": True}},
        )
