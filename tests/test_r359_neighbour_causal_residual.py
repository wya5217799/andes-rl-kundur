"""Public conclusion-seam tests for the R359 causal residual design."""

from __future__ import annotations

import numpy as np
import pytest
from probes.r359_neighbour_causal_residual import (
    build_development_targets,
    build_observations_from_parent_inventory,
    classify_neighbour_causal_gate,
    fit_full_development_controllers,
    leave_one_scenario_out_proposals,
    predict_with_frozen_controllers,
    reconstruct_causal_observations,
)

from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_causal_residual import observation_vector


def test_development_targets_keep_negative_controls_and_zero_startup() -> None:
    targets = build_development_targets(
        scenario_ids=("positive", "negative"),
        candidate_results=(
            {
                "scenario_id": "positive",
                "accepted": True,
                "target_feasible": True,
                "edge_actions": [
                    [0.01, -0.02, 0.03],
                    [0.02, -0.01, 0.00],
                    [0.025, -0.025, 0.05],
                    [-0.05, 0.00, 0.01],
                ],
            },
        ),
        inherited_infeasible_scenario_ids=("negative",),
        horizon=4,
        edge_flow_limit_system_pu=0.05,
        startup_zero_steps=2,
    )

    np.testing.assert_array_equal(targets["negative"], np.zeros((4, 3)))
    np.testing.assert_array_equal(targets["positive"][:2], np.zeros((2, 3)))
    np.testing.assert_allclose(
        targets["positive"][2:],
        np.asarray([[0.5, -0.5, 1.0], [-1.0, 0.0, 0.2]]),
    )


def test_classifier_never_authorizes_training() -> None:
    passed = classify_neighbour_causal_gate(
        integrity_checks={"information": True},
        scientific_checks={"development": True, "holdout": True},
    )
    negative = classify_neighbour_causal_gate(
        integrity_checks={"information": True},
        scientific_checks={"development": False},
    )
    invalid = classify_neighbour_causal_gate(
        integrity_checks={"information": False},
        scientific_checks={"development": True},
    )

    assert passed["classification"] == "NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE"
    assert negative["classification"] == "NO-NEIGHBOUR-CAUSAL-HEADROOM"
    assert invalid["classification"] == "ANALYSIS-INVALID"
    assert passed["training_authorized"] is False
    assert negative["training_authorized"] is False
    assert invalid["training_authorized"] is False


def test_trace_reconstruction_uses_only_completed_pre_action_history() -> None:
    class Bounds:
        def feasible_power_bounds(self, *, previous_power_system_pu, **_kwargs):
            previous = np.asarray(previous_power_system_pu, dtype=float)
            return previous - 1.0, previous + 1.0

    observations = reconstruct_causal_observations(
        frequency_hz_after_action=np.asarray(
            [
                [60.0, 60.0, 60.0, 60.0],
                [60.1, 60.2, 60.3, 60.4],
                [60.5, 60.6, 60.7, 60.8],
            ]
        ),
        commanded_node_power_after_action=np.asarray([[0.0] * 4, [0.1, 0.2, 0.3, 0.4], [0.5] * 4]),
        soc_after_action=np.asarray([[0.4] * 4, [0.41, 0.42, 0.43, 0.44], [0.45] * 4]),
        voltage_after_action=np.asarray([[1.0] * 4, [0.99, 1.01, 1.02, 0.98], [1.0] * 4]),
        executed_edge_flows_after_action=np.asarray([[0.0] * 3, [0.01, 0.02, 0.03], [0.04] * 3]),
        physical_contract=Bounds(),
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
        startup_zero_steps=2,
    )

    assert len(observations[(0, 1)]) == 1
    np.testing.assert_allclose(
        observation_vector(observations[(0, 1)][0]),
        np.asarray(
            [
                0.1,
                0.2,
                0.5,
                1.0,
                0.01,
                0.1,
                0.2,
                0.41,
                0.42,
                0.99,
                1.01,
                -0.9,
                -0.8,
                1.1,
                1.2,
            ]
        ),
        atol=1.0e-12,
    )


def test_parent_inventory_adapter_reads_only_selected_local_causal_trace() -> None:
    class Bounds:
        def feasible_power_bounds(self, *, previous_power_system_pu, **_kwargs):
            previous = np.asarray(previous_power_system_pu, dtype=float)
            return previous - 1.0, previous + 1.0

    rows = [
        {
            "freq_hz_physical": [60.0 + 0.1 * step] * 4,
            "bess_commanded_power_system_pu": [0.01 * step] * 4,
            "bess_soc": [0.5 + 0.01 * step] * 4,
            "bess_bus_voltage_pu": [1.0 - 0.01 * step] * 4,
            "executed_edge_flows_system_pu": [0.001 * step] * 3,
        }
        for step in range(3)
    ]
    observations = build_observations_from_parent_inventory(
        inventory=(
            {
                "scenario_id": "development__FV0__PQ_0__negative",
                "arms": {
                    "zero_edge": {"trace": {"rows": [{"forbidden": True}] * 3}},
                    "selected_local": {"trace": {"rows": rows}},
                },
            },
        ),
        physical_contract=Bounds(),
        nominal_frequency_hz=60.0,
        sample_period_seconds=0.2,
        startup_zero_steps=2,
        expected_horizon=3,
    )

    assert set(observations) == {"development__FV0__PQ_0__negative"}
    assert len(observations["development__FV0__PQ_0__negative"][(0, 1)]) == 1
    assert observation_vector(observations["development__FV0__PQ_0__negative"][(0, 1)][0])[
        0
    ] == pytest.approx(0.1)


def _edge_observation(edge: tuple[int, int], value: float) -> LocalEdgeObservation:
    def endpoint(node_id: int) -> EndpointObservation:
        return EndpointObservation(
            node_id=node_id,
            frequency_deviation_hz=value + node_id * 0.01,
            rocof_hz_s=0.0,
            previous_command_system_pu=0.0,
            soc=0.4,
            voltage_pu=1.0,
            lower_residual_power_system_pu=-0.1,
            upper_residual_power_system_pu=0.1,
        )

    return LocalEdgeObservation(
        edge=edge,
        source=endpoint(edge[0]),
        target=endpoint(edge[1]),
        previous_edge_flow_system_pu=0.0,
    )


def test_leave_one_scenario_out_prediction_cannot_see_heldout_targets() -> None:
    edges = ((0, 1), (1, 2), (2, 3))
    observations = {
        scenario: {
            edge: tuple(_edge_observation(edge, offset + step * 0.1) for step in range(2))
            for edge in edges
        }
        for scenario, offset in (("a", 0.0), ("b", 1.0), ("c", 2.0))
    }
    targets = {
        "a": np.asarray([[0.0] * 3, [0.0] * 3, [0.1] * 3, [0.2] * 3]),
        "b": np.asarray([[0.0] * 3, [0.0] * 3, [0.3] * 3, [0.4] * 3]),
        "c": np.asarray([[0.0] * 3, [0.0] * 3, [0.5] * 3, [0.6] * 3]),
    }
    original = leave_one_scenario_out_proposals(
        observations_by_scenario=observations,
        normalized_targets_by_scenario=targets,
        horizon=4,
        startup_zero_steps=2,
    )
    changed = {**targets, "a": np.full((4, 3), -1.0)}
    changed["a"][:2] = 0.0
    repeated = leave_one_scenario_out_proposals(
        observations_by_scenario=observations,
        normalized_targets_by_scenario=changed,
        horizon=4,
        startup_zero_steps=2,
    )

    np.testing.assert_array_equal(original["a"], repeated["a"])
    np.testing.assert_array_equal(original["a"][:2], np.zeros((2, 3)))


def test_full_development_fit_predicts_unlabelled_scenarios() -> None:
    edges = ((0, 1), (1, 2), (2, 3))
    development_observations = {
        scenario: {
            edge: tuple(_edge_observation(edge, offset + step * 0.1) for step in range(2))
            for edge in edges
        }
        for scenario, offset in (("a", 0.0), ("b", 1.0), ("c", 2.0))
    }
    targets = {
        scenario: np.asarray([[0.0] * 3, [0.0] * 3, [0.1 + offset] * 3, [0.2 + offset] * 3])
        for scenario, offset in (("a", 0.0), ("b", 0.1), ("c", 0.2))
    }
    controllers = fit_full_development_controllers(
        observations_by_scenario=development_observations,
        normalized_targets_by_scenario=targets,
        horizon=4,
        startup_zero_steps=2,
    )
    unlabelled = {
        edge: tuple(_edge_observation(edge, 0.5 + step * 0.1) for step in range(2))
        for edge in edges
    }

    proposal = predict_with_frozen_controllers(
        controllers=controllers,
        observations=unlabelled,
        horizon=4,
        startup_zero_steps=2,
    )

    assert proposal.shape == (4, 3)
    np.testing.assert_array_equal(proposal[:2], np.zeros((2, 3)))
    assert np.all(np.abs(proposal) <= 1.0)
