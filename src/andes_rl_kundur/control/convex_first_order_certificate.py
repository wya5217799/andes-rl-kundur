"""Analytic first-order certificate for a smooth convex program."""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from scipy.optimize import nnls

from andes_rl_kundur.control.minimum_norm_certificate import MinimumNormCertificate


def certify_smooth_convex_first_order(
    *,
    point: object,
    objective_gradient: Callable[[np.ndarray], object],
    constraint_function: Callable[[np.ndarray], object],
    constraint_jacobian: Callable[[np.ndarray], object],
    feasibility_tolerance: float,
) -> MinimumNormCertificate:
    """Certify KKT conditions for smooth convex ``g(x) >= 0`` constraints."""

    values = np.asarray(point, dtype=float)
    tolerance = float(feasibility_tolerance)
    if values.ndim != 1 or values.size < 1 or not np.all(np.isfinite(values)):
        raise ValueError("point must be a non-empty finite vector")
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("feasibility_tolerance must be positive and finite")
    constraints = np.asarray(constraint_function(values), dtype=float)
    if constraints.ndim != 1 or constraints.size < 1 or not np.all(np.isfinite(constraints)):
        raise ValueError("constraint_function must return a non-empty finite vector")
    jacobian = np.asarray(constraint_jacobian(values), dtype=float)
    if (
        jacobian.shape != (constraints.size, values.size)
        or not np.all(np.isfinite(jacobian))
    ):
        raise ValueError(
            "constraint_jacobian must return a finite constraints-by-variables matrix"
        )
    gradient = np.asarray(objective_gradient(values), dtype=float)
    if gradient.shape != values.shape or not np.all(np.isfinite(gradient)):
        raise ValueError("objective_gradient must return one finite value per variable")

    optimality_tolerance = float(np.sqrt(tolerance))
    maximum_violation = float(max(0.0, -float(np.min(constraints))))
    if maximum_violation > tolerance:
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

    active = constraints <= optimality_tolerance
    gradient_scale = max(1.0, float(np.linalg.norm(gradient)))
    if np.any(active):
        active_jacobian = jacobian[active]
        multipliers, _residual = nnls(active_jacobian.T, gradient)
        stationarity = float(
            np.linalg.norm(gradient - active_jacobian.T @ multipliers)
            / gradient_scale
        )
        complementarity = float(
            np.max(np.abs(multipliers * constraints[active]))
        )
    else:
        multipliers = np.empty(0)
        stationarity = float(np.linalg.norm(gradient) / gradient_scale)
        complementarity = 0.0

    valid = bool(
        stationarity <= optimality_tolerance
        and complementarity <= optimality_tolerance
    )
    reason = (
        "certified"
        if valid
        else (
            "stationarity-failed"
            if stationarity > optimality_tolerance
            else "complementarity-failed"
        )
    )
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
