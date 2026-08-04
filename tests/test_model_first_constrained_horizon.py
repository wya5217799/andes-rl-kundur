"""Behavior tests for constrained finite-horizon output feedback."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.model_first_constrained_horizon import (
    simulate_constrained_horizon_feedback,
    solve_constrained_horizon_action,
    synthesize_constrained_horizon,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


def _fully_actuated_realization() -> StateSpaceRealization:
    return StateSpaceRealization(
        state_matrix=np.diag([0.45, 0.50, 0.55, 0.60]),
        input_matrix=0.2 * np.eye(4),
        output_matrix=np.eye(4),
        feedthrough_matrix=0.05 * np.eye(4),
        retained_singular_values=np.ones(4),
    )


def test_constrained_horizon_synthesis_reaches_fixed_observer_template() -> None:
    design = synthesize_constrained_horizon(
        _fully_actuated_realization(),
        output_scales=np.array([1.0, 1.1, 1.2, 1.3]),
        action_scales=np.full(4, 0.36),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
        horizon_steps=5,
    )

    assert design.horizon_steps == 5
    assert design.filter_gain.shape == (8, 4)
    np.testing.assert_allclose(
        np.sort_complex(design.observer_poles),
        np.array([0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]),
        atol=1.0e-10,
    )
    assert design.observer_target_max_abs_error <= 1.0e-8


def test_constrained_horizon_action_respects_all_declared_limits() -> None:
    limits = FeedbackLimits()
    design = synthesize_constrained_horizon(
        _fully_actuated_realization(),
        output_scales=np.ones(4),
        action_scales=np.full(4, limits.node_power),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
        horizon_steps=5,
    )

    solution = solve_constrained_horizon_action(
        design,
        corrected_estimate=np.array([4.0, -3.0, 2.0, -1.0, 0.0, 0.0, 0.0, 0.0]),
        previous_node_action=np.array([0.10, -0.10, 0.05, -0.05]),
        soc=np.array([0.41, 0.51, 0.41, 0.51]),
        limits=limits,
    )

    assert solution.feasible
    assert solution.maximum_constraint_residual <= 1.0e-8
    assert solution.predicted_node_actions.shape == (5, 4)
    assert solution.predicted_coordinate_actions.shape == (5, 4)
    assert np.max(np.abs(solution.predicted_node_actions)) <= limits.node_power + 1.0e-9
    ramps = np.vstack(
        (
            solution.predicted_node_actions[:1]
            - np.array([[0.10, -0.10, 0.05, -0.05]]),
            np.diff(solution.predicted_node_actions, axis=0),
        )
    )
    assert np.max(np.abs(ramps)) <= limits.node_ramp + 1.0e-9
    assert np.min(solution.predicted_soc_lower_envelope) >= limits.minimum_soc - 1.0e-9
    assert np.max(solution.predicted_soc_upper_envelope) <= limits.maximum_soc + 1.0e-9


def test_constrained_horizon_feedback_is_causal_and_needs_no_projection() -> None:
    limits = FeedbackLimits()
    design = synthesize_constrained_horizon(
        _fully_actuated_realization(),
        output_scales=np.ones(4),
        action_scales=np.full(4, limits.node_power),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
        horizon_steps=5,
    )
    disturbances = np.zeros((8, 4))
    disturbances[0, 1] = 0.05

    trace = simulate_constrained_horizon_feedback(
        _fully_actuated_realization(),
        disturbances,
        design=design,
        initial_soc=0.5,
        limits=limits,
    )

    np.testing.assert_allclose(trace.coordinate_actions[0], 0.0, atol=1.0e-12)
    np.testing.assert_allclose(trace.node_actions[0], 0.0, atol=1.0e-12)
    assert trace.solver_failure_count == 0
    assert trace.constraint_violation_count == 0
    assert trace.maximum_constraint_residual <= 1.0e-8
    assert np.max(np.abs(trace.node_actions)) <= limits.node_power + 1.0e-9
    ramps = np.vstack((trace.node_actions[:1], np.diff(trace.node_actions, axis=0)))
    assert np.max(np.abs(ramps)) <= limits.node_ramp + 1.0e-9
    assert np.min(trace.soc) >= limits.minimum_soc - 1.0e-9
    assert np.max(trace.soc) <= limits.maximum_soc + 1.0e-9
