"""Behavior tests for the fixed disturbance-aware estimator seam."""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from andes_rl_kundur.control.model_first_disturbance_estimator import (
    advance_disturbance_estimate,
    synthesize_disturbance_estimator,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


def _realization(*, observable: bool = True) -> StateSpaceRealization:
    return StateSpaceRealization(
        state_matrix=0.8 * np.eye(4),
        input_matrix=0.2 * np.eye(4) if observable else np.zeros((4, 4)),
        output_matrix=np.eye(4) if observable else np.zeros((4, 4)),
        feedthrough_matrix=0.5 * np.eye(4) if observable else np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )


def test_disturbance_estimator_synthesis_is_observable_finite_and_stable() -> None:
    design = synthesize_disturbance_estimator(
        _realization(),
        output_scales=np.ones(4),
        disturbance_scale=0.05,
        measurement_fraction=0.01,
    )

    assert design.physical_state_order == 4
    assert design.observability_rank == 8
    assert design.transition_matrix.shape == (8, 8)
    assert design.measurement_matrix.shape == (4, 8)
    assert design.filter_gain.shape == (8, 4)
    assert design.covariance_symmetry_error <= 1.0e-12
    assert design.covariance_minimum_eigenvalue >= -1.0e-12
    assert design.normalized_covariance_residual <= 1.0e-8
    assert design.error_pole_radius < 1.0


def test_estimator_step_is_causal_deterministic_and_zero_preserving() -> None:
    design = synthesize_disturbance_estimator(_realization(), output_scales=np.ones(4))
    prior = np.zeros(8)
    previous_output = np.zeros(4)
    previous_action = np.zeros(4)

    first = advance_disturbance_estimate(
        design,
        prior_estimate=prior,
        previous_delivered_output=previous_output,
        previous_executed_action=previous_action,
    )
    second = advance_disturbance_estimate(
        design,
        prior_estimate=prior,
        previous_delivered_output=previous_output,
        previous_executed_action=previous_action,
    )

    np.testing.assert_array_equal(first.predicted_estimate, np.zeros(8))
    np.testing.assert_array_equal(first.innovation, np.zeros(4))
    np.testing.assert_array_equal(first.predicted_estimate, second.predicted_estimate)
    assert set(inspect.signature(advance_disturbance_estimate).parameters) == {
        "design",
        "prior_estimate",
        "previous_delivered_output",
        "previous_executed_action",
    }


def test_disturbance_estimator_rejects_unobservable_augmented_model() -> None:
    with pytest.raises(ValueError, match="observable"):
        synthesize_disturbance_estimator(_realization(observable=False), output_scales=np.ones(4))


def test_disturbance_estimator_rejects_invalid_runtime_shapes() -> None:
    design = synthesize_disturbance_estimator(_realization(), output_scales=np.ones(4))
    with pytest.raises(ValueError, match="prior_estimate"):
        advance_disturbance_estimate(
            design,
            prior_estimate=np.zeros(7),
            previous_delivered_output=np.zeros(4),
            previous_executed_action=np.zeros(4),
        )
