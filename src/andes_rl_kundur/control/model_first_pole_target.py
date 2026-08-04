"""Fixed pole-target synthesis for authorized model-first realizations.

This module implements one caller-supplied controller/observer pole template.
It reads no repository artifact, searches no target, runs no disturbance case,
and owns no scientific classification.
"""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.signal import place_poles

from andes_rl_kundur.control.model_first_observer_lqr import (
    ObserverLqrDesign,
    build_delay_augmented_model,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
)


@dataclass(frozen=True)
class FixedPoleTargetDesign:
    """Observable product and diagnostics of one fixed placement call pair."""

    design: ObserverLqrDesign
    controller_poles: np.ndarray
    observer_poles: np.ndarray
    controller_target_max_abs_error: float
    observer_target_max_abs_error: float
    controller_gain_frobenius_norm: float
    observer_gain_frobenius_norm: float
    controller_iterations: int | None
    observer_iterations: int | None
    controller_reported_tolerance: float | None
    observer_reported_tolerance: float | None
    controller_warnings: tuple[str, ...]
    observer_warnings: tuple[str, ...]


def _positive_scales(values: object, *, name: str) -> np.ndarray:
    scales = np.asarray(values, dtype=float)
    if scales.shape != (4,) or not np.all(np.isfinite(scales)) or np.any(scales <= 0):
        raise ValueError(f"{name} must contain four positive finite values")
    return scales


def _target(values: object, dimension: int, *, name: str) -> np.ndarray:
    target = np.asarray(values, dtype=complex)
    if target.shape != (dimension,) or not np.all(np.isfinite(target)):
        raise ValueError(f"{name} must contain one finite pole per augmented state")
    return target


def _target_error(achieved: np.ndarray, target: np.ndarray) -> float:
    cost = np.abs(achieved.reshape(-1, 1) - target.reshape(1, -1))
    rows, columns = linear_sum_assignment(cost)
    return float(np.max(cost[rows, columns]))


def _optional_number(value: object, *, integer: bool) -> int | float | None:
    number = float(value)
    if not np.isfinite(number):
        return None
    return int(number) if integer else number


def synthesize_fixed_pole_target(
    realization: StateSpaceRealization,
    *,
    output_scales: object,
    action_scales: object,
    controller_target_poles: object,
    observer_target_poles: object,
    method: str = "YT",
    relative_tolerance: float = 1.0e-6,
    maximum_iterations: int = 100,
) -> FixedPoleTargetDesign:
    """Place one fixed controller and corrected-state observer template."""

    y_scales = _positive_scales(output_scales, name="output_scales")
    u_scales = _positive_scales(action_scales, name="action_scales")
    augmented = build_delay_augmented_model(realization)
    state = augmented.state_matrix
    inputs = augmented.input_matrix
    measured = augmented.measurement_matrix
    controller_target = _target(
        controller_target_poles, state.shape[0], name="controller_target_poles"
    )
    observer_target = _target(
        observer_target_poles, state.shape[0], name="observer_target_poles"
    )
    tolerance = float(relative_tolerance)
    iterations = int(maximum_iterations)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("relative_tolerance must be positive and finite")
    if iterations < 1:
        raise ValueError("maximum_iterations must be positive")

    with warnings.catch_warnings(record=True) as controller_warning_records:
        warnings.simplefilter("always")
        controller = place_poles(
            state,
            inputs,
            controller_target,
            method=method,
            rtol=tolerance,
            maxiter=iterations,
        )
    with warnings.catch_warnings(record=True) as observer_warning_records:
        warnings.simplefilter("always")
        corrected_observer = place_poles(
            state.T,
            (measured @ state).T,
            observer_target,
            method=method,
            rtol=tolerance,
            maxiter=iterations,
        )

    feedback = np.asarray(controller.gain_matrix, dtype=float)
    filter_gain = np.asarray(corrected_observer.gain_matrix.T, dtype=float)
    controller_poles = np.linalg.eigvals(state - inputs @ feedback)
    observer_poles = np.linalg.eigvals(
        (np.eye(state.shape[0]) - filter_gain @ measured) @ state
    )
    values = (feedback, filter_gain, controller_poles, observer_poles)
    if not all(np.all(np.isfinite(value)) for value in values):
        raise ValueError("fixed pole placement returned non-finite values")

    design = ObserverLqrDesign(
        augmented_model=augmented,
        feedback_gain=feedback,
        filter_gain=filter_gain,
        output_scales=y_scales.copy(),
        action_scales=u_scales.copy(),
        controller_pole_radius=float(np.max(np.abs(controller_poles))),
        observer_pole_radius=float(np.max(np.abs(observer_poles))),
    )
    return FixedPoleTargetDesign(
        design=design,
        controller_poles=controller_poles,
        observer_poles=observer_poles,
        controller_target_max_abs_error=_target_error(
            controller_poles, controller_target
        ),
        observer_target_max_abs_error=_target_error(observer_poles, observer_target),
        controller_gain_frobenius_norm=float(np.linalg.norm(feedback)),
        observer_gain_frobenius_norm=float(np.linalg.norm(filter_gain)),
        controller_iterations=_optional_number(controller.nb_iter, integer=True),
        observer_iterations=_optional_number(corrected_observer.nb_iter, integer=True),
        controller_reported_tolerance=_optional_number(controller.rtol, integer=False),
        observer_reported_tolerance=_optional_number(
            corrected_observer.rtol, integer=False
        ),
        controller_warnings=tuple(str(item.message) for item in controller_warning_records),
        observer_warnings=tuple(str(item.message) for item in observer_warning_records),
    )
