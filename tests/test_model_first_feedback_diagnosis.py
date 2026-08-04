"""Behavior tests for development-only feedback diagnosis seams."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.model_first_feedback_diagnosis import (
    derive_common_authority_scale,
    diagnose_observer_feedback_commands,
    scale_observer_feedback_design,
    simulate_exact_state_feedback,
)
from andes_rl_kundur.control.model_first_observer_lqr import (
    simulate_observer_lqr_feedback,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_pole_target import (
    synthesize_fixed_pole_target,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


def _realization() -> StateSpaceRealization:
    return StateSpaceRealization(
        state_matrix=0.55 * np.eye(4),
        input_matrix=0.2 * np.eye(4),
        output_matrix=np.eye(4),
        feedthrough_matrix=0.05 * np.eye(4),
        retained_singular_values=np.ones(4),
    )


def _design():
    return synthesize_fixed_pole_target(
        _realization(),
        output_scales=np.ones(4),
        action_scales=np.ones(4),
        controller_target_poles=np.array(
            [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
        ),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
    ).design


def test_command_diagnosis_replays_trace_and_splits_true_state_from_error() -> None:
    disturbance = np.zeros((8, 4))
    disturbance[0, 0] = 0.05
    limits = FeedbackLimits(node_power=0.2, node_ramp=0.05)
    trace = simulate_observer_lqr_feedback(
        _realization(),
        disturbance,
        design=_design(),
        initial_soc=0.5,
        limits=limits,
    )

    diagnosis = diagnose_observer_feedback_commands(
        _realization(),
        disturbance,
        design=_design(),
        trace=trace,
        limits=limits,
    )

    np.testing.assert_allclose(
        diagnosis.raw_observer_node_actions,
        diagnosis.true_state_node_actions + diagnosis.estimation_error_node_actions,
        atol=1.0e-12,
    )
    assert diagnosis.maximum_decomposition_error <= 1.0e-12
    assert diagnosis.maximum_output_replay_error <= 1.0e-12
    assert diagnosis.maximum_action_replay_error <= 1.0e-12
    assert diagnosis.raw_node_power_ratio >= 0.0
    assert diagnosis.raw_node_ramp_ratio >= 0.0


def test_exact_state_counterfactual_and_common_scale_respect_public_limits() -> None:
    disturbance = np.zeros((8, 4))
    disturbance[0, 0] = 0.05
    limits = FeedbackLimits(node_power=0.02, node_ramp=0.005)
    design = _design()
    observer_trace = simulate_observer_lqr_feedback(
        _realization(),
        disturbance,
        design=design,
        initial_soc=0.5,
        limits=limits,
    )
    diagnosis = diagnose_observer_feedback_commands(
        _realization(),
        disturbance,
        design=design,
        trace=observer_trace,
        limits=limits,
    )
    exact = simulate_exact_state_feedback(
        _realization(),
        disturbance,
        design=design,
        initial_soc=0.5,
        limits=limits,
    )
    scale = derive_common_authority_scale([diagnosis])
    scaled = scale_observer_feedback_design(design, scale)

    assert 0.0 < scale <= 1.0
    np.testing.assert_allclose(scaled.feedback_gain, scale * design.feedback_gain)
    np.testing.assert_allclose(scaled.filter_gain, design.filter_gain)
    assert np.max(np.abs(exact.node_actions)) <= limits.node_power + 1.0e-12
    assert np.max(
        np.abs(np.vstack((exact.node_actions[:1], np.diff(exact.node_actions, axis=0))))
    ) <= limits.node_ramp + 1.0e-12
    assert exact.constraint_violation_count == 0
