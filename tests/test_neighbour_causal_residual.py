"""Behavior tests for the exact-information causal residual seam."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from andes_rl_kundur.control.model_first_distributed_edge import (
    EndpointObservation,
    LocalEdgeObservation,
)
from andes_rl_kundur.control.neighbour_causal_residual import (
    fit_affine_edge_controller,
    observation_vector,
)


def _observation() -> LocalEdgeObservation:
    return LocalEdgeObservation(
        edge=(1, 2),
        source=EndpointObservation(
            node_id=1,
            frequency_deviation_hz=0.1,
            rocof_hz_s=0.2,
            previous_command_system_pu=0.3,
            soc=0.4,
            voltage_pu=0.5,
            lower_residual_power_system_pu=-0.6,
            upper_residual_power_system_pu=0.7,
        ),
        target=EndpointObservation(
            node_id=2,
            frequency_deviation_hz=-0.1,
            rocof_hz_s=-0.2,
            previous_command_system_pu=-0.3,
            soc=0.45,
            voltage_pu=1.05,
            lower_residual_power_system_pu=-0.65,
            upper_residual_power_system_pu=0.75,
        ),
        previous_edge_flow_system_pu=0.08,
    )


def test_observation_vector_is_the_exact_fifteen_field_public_contract() -> None:
    observed = observation_vector(_observation())

    np.testing.assert_array_equal(
        observed,
        np.asarray(
            [
                0.1,
                -0.1,
                0.2,
                -0.2,
                0.08,
                0.3,
                -0.3,
                0.4,
                0.45,
                0.5,
                1.05,
                -0.6,
                -0.65,
                0.7,
                0.75,
            ]
        ),
    )


def test_affine_edge_controller_fits_and_clips_one_normalized_local_action() -> None:
    base = _observation()
    observations = [
        replace(
            base,
            source=replace(base.source, frequency_deviation_hz=value),
        )
        for value in (-0.2, 0.0, 0.2)
    ]
    controller = fit_affine_edge_controller(
        edge=(1, 2),
        observations=observations,
        normalized_actions=(-0.4, 0.0, 0.4),
    )

    np.testing.assert_allclose(controller.act(observations[2]), 0.4, atol=1.0e-12)
    extreme = replace(
        base,
        source=replace(base.source, frequency_deviation_hz=2.0),
    )
    assert controller.act(extreme) == 1.0
