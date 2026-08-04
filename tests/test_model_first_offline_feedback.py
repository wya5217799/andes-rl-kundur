"""Behavior tests for the model-first offline feedback public seam."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.model_first_offline_feedback import (
    FeedbackCase,
    FeedbackLimits,
    augmented_closed_loop_radius,
    select_scalar_multiplier,
    simulate_delayed_output_feedback,
    synthesize_dc_inverse_gains,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


def _static_realization(dc_gain: np.ndarray) -> StateSpaceRealization:
    return StateSpaceRealization(
        state_matrix=np.zeros((4, 4)),
        input_matrix=np.eye(4),
        output_matrix=np.zeros((4, 4)),
        feedthrough_matrix=np.asarray(dc_gain, dtype=float),
        retained_singular_values=np.ones(4),
    )


def test_synthesis_deletes_only_common_differential_feedback_blocks() -> None:
    retained_expected = np.array(
        [
            [2.0, 0.5, -0.25, 0.125],
            [0.4, 1.5, 0.3, -0.2],
            [-0.2, 0.1, 1.2, 0.25],
            [0.1, -0.15, 0.2, 1.1],
        ]
    )
    family = synthesize_dc_inverse_gains(
        [_static_realization(np.linalg.inv(retained_expected))]
    )

    deleted_expected = retained_expected.copy()
    deleted_expected[0, 1:] = 0.0
    deleted_expected[1:, 0] = 0.0
    np.testing.assert_allclose(family.retained_cross_base, retained_expected)
    np.testing.assert_allclose(family.cross_deleted_base, deleted_expected)
    np.testing.assert_allclose(
        family.averaged_dc_gain,
        np.linalg.inv(retained_expected),
    )


def test_feedback_uses_one_sample_delay_and_returns_physical_node_actions() -> None:
    realization = _static_realization(np.eye(4))
    disturbance = np.zeros((3, 4))
    disturbance[0, 0] = 0.05

    trace = simulate_delayed_output_feedback(
        realization,
        disturbance,
        gain=np.eye(4),
        initial_soc=0.5,
        limits=FeedbackLimits(node_power=1.0, node_ramp=1.0),
    )

    np.testing.assert_allclose(trace.coordinate_actions[0], np.zeros(4), atol=1e-15)
    np.testing.assert_allclose(
        trace.coordinate_actions[1], [-0.05, 0.0, 0.0, 0.0], atol=1e-15
    )
    np.testing.assert_allclose(trace.node_actions[1], [-0.05] * 4, atol=1e-15)
    np.testing.assert_allclose(
        trace.outputs[0], [0.05, 0.0, 0.0, 0.0], atol=1e-15
    )
    np.testing.assert_allclose(
        trace.outputs[1], [-0.05, 0.0, 0.0, 0.0], atol=1e-15
    )


def test_feedback_governor_enforces_node_ramp_power_and_soc_limits() -> None:
    realization = _static_realization(np.eye(4))
    disturbance = np.zeros((4, 4))
    disturbance[0, 0] = 1.0

    trace = simulate_delayed_output_feedback(
        realization,
        disturbance,
        gain=10.0 * np.eye(4),
        initial_soc=0.2,
        limits=FeedbackLimits(node_power=0.05, node_ramp=0.02),
    )

    assert np.max(np.abs(trace.node_actions)) <= 0.05
    assert np.max(np.abs(np.diff(trace.node_actions, axis=0))) <= 0.02 + 1e-12
    assert np.min(trace.soc) >= 0.2
    assert np.max(trace.soc) <= 0.8
    assert trace.governor_intervention_count > 0
    assert trace.constraint_violation_count == 0


def test_augmented_pole_radius_includes_the_one_sample_output_delay() -> None:
    realization = StateSpaceRealization(
        state_matrix=np.zeros((4, 4)),
        input_matrix=np.eye(4),
        output_matrix=np.eye(4),
        feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )

    radius = augmented_closed_loop_radius(realization, 0.25 * np.eye(4))

    assert np.isclose(radius, 0.5, rtol=0.0, atol=1e-12)


def test_scalar_selection_uses_equal_declared_candidates_and_fixed_tie_breaks() -> None:
    realization = _static_realization(np.eye(4))
    disturbance = np.zeros((4, 4))
    disturbance[0, 0] = 0.05
    selection = select_scalar_multiplier(
        {"P0": realization},
        [FeedbackCase("P0", "impulse/common/positive", disturbance, 0.5)],
        base_gain=np.eye(4),
        scalar_candidates=(0.1, 0.2),
        limits=FeedbackLimits(node_power=1.0, node_ramp=1.0),
        maximum_pole_radius=0.995,
    )

    assert selection.scalar == 0.1
    assert selection.candidate_count == 2
    assert selection.case_count == 1
    assert selection.constraint_violation_count == 0
