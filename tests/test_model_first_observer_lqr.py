"""Behavior tests for the model-first observer-LQR public seam."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.model_first_observer_lqr import (
    build_delay_augmented_model,
    delete_common_differential_markov_blocks,
    simulate_observer_lqr_feedback,
    synthesize_observer_lqr,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


def _realization() -> StateSpaceRealization:
    return StateSpaceRealization(
        state_matrix=np.array([[0.8]]),
        input_matrix=np.array([[1.0, 2.0, 3.0, 4.0]]),
        output_matrix=np.array([[1.0], [2.0], [3.0], [4.0]]),
        feedthrough_matrix=np.arange(16, dtype=float).reshape(4, 4) / 100.0,
        retained_singular_values=np.ones(1),
    )


def test_delay_augmentation_and_cross_deletion_change_only_declared_blocks() -> None:
    realization = _realization()
    augmented = build_delay_augmented_model(realization)

    np.testing.assert_allclose(
        augmented.state_matrix,
        np.block(
            [
                [realization.state_matrix, np.zeros((1, 4))],
                [realization.output_matrix, np.zeros((4, 4))],
            ]
        ),
    )
    np.testing.assert_allclose(
        augmented.input_matrix,
        np.vstack((realization.input_matrix, realization.feedthrough_matrix)),
    )
    np.testing.assert_allclose(
        augmented.measurement_matrix,
        np.hstack((np.zeros((4, 1)), np.eye(4))),
    )

    markov = np.arange(3 * 4 * 4, dtype=float).reshape(3, 4, 4)
    deleted = delete_common_differential_markov_blocks(markov)
    expected = markov.copy()
    expected[:, 0, 1:] = 0.0
    expected[:, 1:, 0] = 0.0
    np.testing.assert_allclose(deleted, expected)
    np.testing.assert_allclose(markov, np.arange(48).reshape(3, 4, 4))


def test_observer_lqr_synthesis_returns_finite_stable_full_order_gains() -> None:
    realization = StateSpaceRealization(
        state_matrix=0.8 * np.eye(4),
        input_matrix=0.2 * np.eye(4),
        output_matrix=np.eye(4),
        feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )

    design = synthesize_observer_lqr(
        realization,
        output_scales=np.ones(4),
        action_scales=np.ones(4),
    )

    assert design.feedback_gain.shape == (4, 8)
    assert design.filter_gain.shape == (8, 4)
    assert np.all(np.isfinite(design.feedback_gain))
    assert np.all(np.isfinite(design.filter_gain))
    assert design.controller_pole_radius < 0.995
    assert design.observer_pole_radius < 0.995


def test_observer_feedback_is_causal_and_returns_governed_node_actions() -> None:
    realization = StateSpaceRealization(
        state_matrix=0.5 * np.eye(4),
        input_matrix=0.5 * np.eye(4),
        output_matrix=np.eye(4),
        feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    design = synthesize_observer_lqr(
        realization,
        output_scales=np.ones(4),
        action_scales=np.ones(4),
    )
    disturbance = np.zeros((5, 4))
    disturbance[0, 0] = 0.05

    trace = simulate_observer_lqr_feedback(
        realization,
        disturbance,
        design=design,
        initial_soc=0.5,
        limits=FeedbackLimits(node_power=1.0, node_ramp=1.0),
    )

    np.testing.assert_allclose(trace.coordinate_actions[0], np.zeros(4), atol=1e-15)
    assert np.linalg.norm(trace.coordinate_actions[1:]) > 0.0
    assert trace.node_actions.shape == (5, 4)
    assert trace.innovations.shape == (5, 4)
    assert np.all(np.isfinite(trace.outputs))
    assert np.all(np.isfinite(trace.estimates))
    assert trace.constraint_violation_count == 0
