from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    IndependentNeighbourEdgeExecution,
    JointInformationEdgeController,
    LinearNeighbourEdgeController,
    LocalEdgeObservation,
    MatchedEdgeActionGovernor,
)


def _endpoint(
    node_id: int,
    *,
    frequency_deviation_hz: float,
    rocof_hz_s: float,
) -> EndpointObservation:
    return EndpointObservation(
        node_id=node_id,
        frequency_deviation_hz=frequency_deviation_hz,
        rocof_hz_s=rocof_hz_s,
        previous_command_system_pu=0.0,
        soc=0.5,
        voltage_pu=1.0,
        lower_residual_power_system_pu=-0.05,
        upper_residual_power_system_pu=0.05,
    )


def test_local_edge_policy_has_only_endpoint_information_and_one_action() -> None:
    assert [field.name for field in fields(LocalEdgeObservation)] == [
        "edge",
        "source",
        "target",
        "previous_edge_flow_system_pu",
    ]
    observation = LocalEdgeObservation(
        edge=(0, 1),
        source=_endpoint(
            0,
            frequency_deviation_hz=-0.1,
            rocof_hz_s=-0.2,
        ),
        target=_endpoint(
            1,
            frequency_deviation_hz=0.1,
            rocof_hz_s=0.2,
        ),
        previous_edge_flow_system_pu=0.0,
    )
    controller = LinearNeighbourEdgeController(
        edge=(0, 1),
        frequency_difference_gain_per_hz=2.0,
        rocof_difference_gain_s_per_hz=0.5,
    )

    action = controller.act(observation)

    assert action == pytest.approx(0.6)


def test_matched_governor_maps_three_actions_through_physical_limits() -> None:
    governor = MatchedEdgeActionGovernor(
        physical_contract=r272_frozen_bess_contract(),
        edge_flow_limit_system_pu=0.05,
        edge_slew_limit_system_pu=0.05,
    )

    result = governor.govern(
        normalized_edge_actions=[0.4, -0.2, 0.3],
        previous_edge_flows_system_pu=[0.0, 0.0, 0.0],
        base_power_request_system_pu=[0.0, 0.0, 0.0, 0.0],
        previous_commanded_power_system_pu=[0.0, 0.0, 0.0, 0.0],
        soc=[0.5, 0.5, 0.5, 0.5],
        voltage_pu=[1.0, 1.0, 1.0, 1.0],
        dt_seconds=0.2,
    )

    np.testing.assert_allclose(
        result.requested_edge_flows_system_pu,
        [0.02, -0.01, 0.015],
        atol=1e-12,
    )
    np.testing.assert_allclose(
        result.executed_edge_flows_system_pu,
        [0.02, -0.01, 0.015],
        atol=1e-12,
    )
    np.testing.assert_allclose(
        result.node_residual_power_system_pu,
        [0.02, -0.03, 0.025, -0.015],
        atol=1e-12,
    )
    np.testing.assert_allclose(
        result.physical_projection.commanded_power_system_pu,
        result.node_residual_power_system_pu,
        atol=1e-12,
    )
    assert float(np.sum(result.node_residual_power_system_pu)) == pytest.approx(
        0.0, abs=1e-12
    )


def _edge_observation(
    edge: tuple[int, int],
    frequencies: list[float],
) -> LocalEdgeObservation:
    source, target = edge
    return LocalEdgeObservation(
        edge=edge,
        source=_endpoint(
            source,
            frequency_deviation_hz=frequencies[source],
            rocof_hz_s=0.0,
        ),
        target=_endpoint(
            target,
            frequency_deviation_hz=frequencies[target],
            rocof_hz_s=0.0,
        ),
        previous_edge_flow_system_pu=0.0,
    )


def test_independent_edge_execution_has_no_nonendpoint_influence() -> None:
    edges = ((0, 1), (1, 2), (2, 3))
    execution = IndependentNeighbourEdgeExecution(
        tuple(
            LinearNeighbourEdgeController(
                edge=edge,
                frequency_difference_gain_per_hz=1.0,
                rocof_difference_gain_s_per_hz=0.0,
            )
            for edge in edges
        )
    )
    nominal = {
        edge: _edge_observation(edge, [0.0, 0.0, 0.0, 0.0]) for edge in edges
    }
    changed = {
        edge: _edge_observation(edge, [-0.1, 0.0, 0.0, 0.0]) for edge in edges
    }

    np.testing.assert_allclose(execution.act(nominal), [0.0, 0.0, 0.0])
    np.testing.assert_allclose(execution.act(changed), [0.1, 0.0, 0.0])


def test_joint_information_upper_returns_the_same_three_edge_coordinates() -> None:
    endpoints = {
        index: _endpoint(
            index,
            frequency_deviation_hz=1.0 if index == 0 else 0.0,
            rocof_hz_s=0.0,
        )
        for index in range(4)
    }
    controller = JointInformationEdgeController(
        frequency_difference_gain_per_hz=1.0,
        rocof_difference_gain_s_per_hz=0.0,
    )

    action = controller.act(endpoints)

    assert controller.architecture == "joint_information_three_edge_upper_reference"
    assert action.shape == (3,)
    np.testing.assert_allclose(action, [-0.75, -0.50, -0.25], atol=1e-12)
