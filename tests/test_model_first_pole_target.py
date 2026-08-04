"""Behavior tests for the fixed pole-target synthesis public seam."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.model_first_pole_target import (
    synthesize_fixed_pole_target,
)
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


def test_fixed_pole_target_synthesis_reaches_the_single_declared_template() -> None:
    result = synthesize_fixed_pole_target(
        _fully_actuated_realization(),
        output_scales=np.array([1.0, 1.1, 1.2, 1.3]),
        action_scales=np.array([0.4, 0.4, 0.4, 0.4]),
        controller_target_poles=np.array(
            [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
        ),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
        method="YT",
        relative_tolerance=1.0e-6,
        maximum_iterations=100,
    )

    np.testing.assert_allclose(
        np.sort_complex(result.controller_poles),
        np.array([0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]),
        atol=1.0e-10,
    )
    np.testing.assert_allclose(
        np.sort_complex(result.observer_poles),
        np.array([0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]),
        atol=1.0e-10,
    )
    assert result.design.feedback_gain.shape == (4, 8)
    assert result.design.filter_gain.shape == (8, 4)
    assert result.controller_target_max_abs_error <= 1.0e-8
    assert result.observer_target_max_abs_error <= 1.0e-8
    assert np.isfinite(result.controller_gain_frobenius_norm)
    assert np.isfinite(result.observer_gain_frobenius_norm)


def test_fixed_pole_target_observer_uses_corrected_state_timing() -> None:
    result = synthesize_fixed_pole_target(
        _fully_actuated_realization(),
        output_scales=np.ones(4),
        action_scales=np.ones(4),
        controller_target_poles=np.array(
            [0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50, 0.55]
        ),
        observer_target_poles=np.array(
            [0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]
        ),
    )

    model = result.design.augmented_model
    corrected = (
        np.eye(model.state_matrix.shape[0])
        - result.design.filter_gain @ model.measurement_matrix
    ) @ model.state_matrix
    conventional = (
        model.state_matrix
        - result.design.filter_gain @ model.measurement_matrix
    )
    np.testing.assert_allclose(
        np.sort_complex(np.linalg.eigvals(corrected)),
        np.array([0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]),
        atol=1.0e-10,
    )
    assert not np.allclose(
        np.sort_complex(np.linalg.eigvals(conventional)),
        np.array([0.0, 0.0, 0.0, 0.0, 0.10, 0.15, 0.20, 0.25]),
        atol=1.0e-2,
    )
