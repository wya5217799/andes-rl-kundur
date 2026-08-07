"""Independent first-order certificate for convex minimum-norm solutions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy.optimize import nnls


@dataclass(frozen=True)
class MinimumNormCertificate:
    """Feasibility and KKT certificate for ``min ||x||_2^2``."""

    valid: bool
    feasible: bool
    reason: str
    active_constraint_count: int
    maximum_constraint_violation: float
    stationarity_residual: float
    complementarity_residual: float
    optimality_tolerance: float
    multipliers: np.ndarray


def _constraint_vector(
    function: Callable[[np.ndarray], object],
    point: np.ndarray,
) -> np.ndarray:
    values = np.asarray(function(point), dtype=float)
    if values.ndim != 1 or values.size < 1 or not np.all(np.isfinite(values)):
        raise ValueError("constraint_function must return a non-empty finite vector")
    return values


def _central_jacobian(
    function: Callable[[np.ndarray], object],
    point: np.ndarray,
    output_size: int,
) -> np.ndarray:
    step_scale = float(np.cbrt(np.finfo(float).eps))
    jacobian = np.empty((output_size, point.size))
    for index in range(point.size):
        step = step_scale * max(1.0, abs(float(point[index])))
        upper = point.copy()
        lower = point.copy()
        upper[index] += step
        lower[index] -= step
        upper_values = _constraint_vector(function, upper)
        lower_values = _constraint_vector(function, lower)
        if upper_values.size != output_size or lower_values.size != output_size:
            raise ValueError("constraint_function output size changed under perturbation")
        jacobian[:, index] = (upper_values - lower_values) / (2.0 * step)
    if not np.all(np.isfinite(jacobian)):
        raise ValueError("constraint Jacobian is non-finite")
    return jacobian


def certify_convex_minimum_norm(
    *,
    point: object,
    constraint_function: Callable[[np.ndarray], object],
    feasibility_tolerance: float,
    nonconvex_constraint_slacks: object | None = None,
) -> MinimumNormCertificate:
    """Certify one feasible KKT point independently of solver status.

    Constraints use the convention ``g(x) >= 0``.  The caller must supply a
    dimensionless convex constraint vector.  Any separately identified
    nonconvex constraints must be strictly inactive for this certificate to be
    sufficient.
    """

    values = np.asarray(point, dtype=float)
    tolerance = float(feasibility_tolerance)
    if values.ndim != 1 or values.size < 1 or not np.all(np.isfinite(values)):
        raise ValueError("point must be a non-empty finite vector")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")
    optimality_tolerance = float(np.sqrt(tolerance))
    constraints = _constraint_vector(constraint_function, values)
    maximum_violation = float(max(0.0, -float(np.min(constraints))))
    feasible = maximum_violation <= tolerance
    if not feasible:
        return MinimumNormCertificate(
            valid=False,
            feasible=False,
            reason="constraint-infeasible",
            active_constraint_count=0,
            maximum_constraint_violation=maximum_violation,
            stationarity_residual=float("inf"),
            complementarity_residual=float("inf"),
            optimality_tolerance=optimality_tolerance,
            multipliers=np.empty(0),
        )

    if nonconvex_constraint_slacks is not None:
        nonconvex = np.asarray(nonconvex_constraint_slacks, dtype=float)
        if nonconvex.ndim != 1 or not np.all(np.isfinite(nonconvex)):
            raise ValueError("nonconvex_constraint_slacks must be a finite vector")
        if np.any(nonconvex <= optimality_tolerance):
            return MinimumNormCertificate(
                valid=False,
                feasible=True,
                reason="nonconvex-constraint-active",
                active_constraint_count=0,
                maximum_constraint_violation=maximum_violation,
                stationarity_residual=float("inf"),
                complementarity_residual=float("inf"),
                optimality_tolerance=optimality_tolerance,
                multipliers=np.empty(0),
            )

    active = constraints <= optimality_tolerance
    gradient = 2.0 * values
    gradient_scale = max(1.0, float(np.linalg.norm(gradient)))
    if np.any(active):
        jacobian = _central_jacobian(
            constraint_function,
            values,
            constraints.size,
        )[active]
        multipliers, _residual = nnls(jacobian.T, gradient)
        stationarity = float(np.linalg.norm(gradient - jacobian.T @ multipliers) / gradient_scale)
        complementarity = float(np.max(np.abs(multipliers * constraints[active])))
    else:
        multipliers = np.empty(0)
        stationarity = float(np.linalg.norm(gradient) / gradient_scale)
        complementarity = 0.0

    stationarity_pass = stationarity <= optimality_tolerance
    complementarity_pass = complementarity <= optimality_tolerance
    valid = bool(stationarity_pass and complementarity_pass)
    if valid:
        reason = "certified"
    elif not stationarity_pass:
        reason = "stationarity-failed"
    else:
        reason = "complementarity-failed"
    return MinimumNormCertificate(
        valid=valid,
        feasible=True,
        reason=reason,
        active_constraint_count=int(np.count_nonzero(active)),
        maximum_constraint_violation=maximum_violation,
        stationarity_residual=stationarity,
        complementarity_residual=complementarity,
        optimality_tolerance=optimality_tolerance,
        multipliers=np.asarray(multipliers, dtype=float),
    )
