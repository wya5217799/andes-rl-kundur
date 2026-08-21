#!/usr/bin/env python3
"""Prospective, non-training tools for a matched DAE action-authority comparison.

The functions implement the *calculation framework* requested by the audit:
index-1 DAE elimination, zero-order-hold discretization, finite-horizon lifted
response maps, projected authority metrics, and common-gradient negligibility
checks. They do not contain project Jacobians, so they produce no plant evidence
until actual operating-point matrices are supplied.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import expm

FloatMatrix = NDArray[np.float64]


@dataclass(frozen=True)
class ReducedDAE:
    """Reduced state/input/output matrices after index-1 algebraic elimination."""

    A: FloatMatrix
    B_u: FloatMatrix
    B_w: FloatMatrix | None = None
    C: FloatMatrix | None = None
    D_u: FloatMatrix | None = None
    D_w: FloatMatrix | None = None
    gy_condition_number: float | None = None


@dataclass(frozen=True)
class AuthorityMetrics:
    """Finite-horizon metrics for one normalized action object."""

    singular_values: FloatMatrix
    spectral_norm: float
    minimum_nonzero_singular_value: float
    numerical_rank: int
    condition_number_nonzero: float
    projected_common_norm: float | None
    projected_differential_norm: float | None


def _as_2d(name: str, value: ArrayLike) -> FloatMatrix:
    array = np.asarray(value, dtype=float)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a 2-D array; received shape {array.shape}.")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values.")
    return array


def reduce_index1_dae(
    f_x: ArrayLike,
    f_y: ArrayLike,
    f_u: ArrayLike,
    g_x: ArrayLike,
    g_y: ArrayLike,
    g_u: ArrayLike,
    *,
    f_w: ArrayLike | None = None,
    g_w: ArrayLike | None = None,
    h_x: ArrayLike | None = None,
    h_y: ArrayLike | None = None,
    h_u: ArrayLike | None = None,
    h_w: ArrayLike | None = None,
    max_gy_condition: float = 1e10,
) -> ReducedDAE:
    """Eliminate algebraic variables from an index-1 DAE linearization.

    The state and input reductions are

        A_r   = f_x - f_y g_y^{-1} g_x
        B_u,r = f_u - f_y g_y^{-1} g_u.

    Optional disturbance and output matrices are reduced consistently. Solves
    are used instead of forming ``g_y^{-1}`` explicitly.
    """

    fx = _as_2d("f_x", f_x)
    fy = _as_2d("f_y", f_y)
    fu = _as_2d("f_u", f_u)
    gx = _as_2d("g_x", g_x)
    gy = _as_2d("g_y", g_y)
    gu = _as_2d("g_u", g_u)

    nx = fx.shape[0]
    if fx.shape != (nx, nx):
        raise ValueError("f_x must be square.")
    ny = gy.shape[0]
    if gy.shape != (ny, ny):
        raise ValueError("g_y must be square.")
    if fy.shape != (nx, ny):
        raise ValueError("f_y has incompatible shape.")
    if gx.shape != (ny, nx):
        raise ValueError("g_x has incompatible shape.")
    if fu.shape[0] != nx or gu.shape != (ny, fu.shape[1]):
        raise ValueError("f_u and g_u have incompatible input dimensions.")

    cond_gy = float(np.linalg.cond(gy))
    if not np.isfinite(cond_gy) or cond_gy > max_gy_condition:
        raise np.linalg.LinAlgError(
            f"g_y is singular or too ill-conditioned for reliable elimination: cond={cond_gy:.3e}."
        )

    solved_gx = np.linalg.solve(gy, gx)
    solved_gu = np.linalg.solve(gy, gu)
    ar = fx - fy @ solved_gx
    bur = fu - fy @ solved_gu

    bwr: FloatMatrix | None = None
    if (f_w is None) ^ (g_w is None):
        raise ValueError("Supply both f_w and g_w, or neither.")
    if f_w is not None and g_w is not None:
        fw = _as_2d("f_w", f_w)
        gw = _as_2d("g_w", g_w)
        if fw.shape[0] != nx or gw.shape != (ny, fw.shape[1]):
            raise ValueError("f_w and g_w have incompatible disturbance dimensions.")
        bwr = fw - fy @ np.linalg.solve(gy, gw)

    cr: FloatMatrix | None = None
    dur: FloatMatrix | None = None
    dwr: FloatMatrix | None = None
    if h_x is not None or h_y is not None:
        if h_x is None or h_y is None:
            raise ValueError("Supply both h_x and h_y to reduce an output map.")
        hx = _as_2d("h_x", h_x)
        hy = _as_2d("h_y", h_y)
        if hx.shape[1] != nx or hy.shape != (hx.shape[0], ny):
            raise ValueError("h_x and h_y have incompatible output dimensions.")
        cr = hx - hy @ solved_gx

        hu = np.zeros((hx.shape[0], fu.shape[1])) if h_u is None else _as_2d("h_u", h_u)
        if hu.shape != (hx.shape[0], fu.shape[1]):
            raise ValueError("h_u has incompatible shape.")
        dur = hu - hy @ solved_gu

        if bwr is not None:
            hw = (
                np.zeros((hx.shape[0], bwr.shape[1]))
                if h_w is None
                else _as_2d("h_w", h_w)
            )
            if hw.shape != (hx.shape[0], bwr.shape[1]):
                raise ValueError("h_w has incompatible shape.")
            assert g_w is not None
            dwr = hw - hy @ np.linalg.solve(gy, _as_2d("g_w", g_w))

    return ReducedDAE(
        A=ar,
        B_u=bur,
        B_w=bwr,
        C=cr,
        D_u=dur,
        D_w=dwr,
        gy_condition_number=cond_gy,
    )


def zoh_discretize(A: ArrayLike, B: ArrayLike, dt: float) -> tuple[FloatMatrix, FloatMatrix]:
    """Exact zero-order-hold discretization using one augmented matrix exponential."""

    a = _as_2d("A", A)
    b = _as_2d("B", B)
    if a.shape[0] != a.shape[1] or b.shape[0] != a.shape[0]:
        raise ValueError("A must be square and B must have matching rows.")
    if dt <= 0:
        raise ValueError("dt must be positive.")

    n, m = b.shape
    augmented = np.zeros((n + m, n + m), dtype=float)
    augmented[:n, :n] = a
    augmented[:n, n:] = b
    transition = expm(augmented * float(dt))
    return transition[:n, :n], transition[:n, n:]


def lifted_response_map(
    A_d: ArrayLike,
    B_d: ArrayLike,
    C: ArrayLike,
    D: ArrayLike | None,
    horizon: int,
) -> FloatMatrix:
    """Map a stacked input sequence to stacked outputs over ``horizon`` steps.

    The convention is ``x[k+1] = A_d x[k] + B_d u[k]`` and
    ``y[k] = C x[k] + D u[k]``, with zero initial state.
    """

    ad = _as_2d("A_d", A_d)
    bd = _as_2d("B_d", B_d)
    c = _as_2d("C", C)
    if ad.shape[0] != ad.shape[1] or bd.shape[0] != ad.shape[0] or c.shape[1] != ad.shape[0]:
        raise ValueError("A_d, B_d, and C have incompatible shapes.")
    if horizon <= 0:
        raise ValueError("horizon must be positive.")

    p, m = c.shape[0], bd.shape[1]
    direct = np.zeros((p, m), dtype=float) if D is None else _as_2d("D", D)
    if direct.shape != (p, m):
        raise ValueError("D has incompatible shape.")

    lifted = np.zeros((p * horizon, m * horizon), dtype=float)
    powers: list[FloatMatrix] = [np.eye(ad.shape[0])]
    for _ in range(1, horizon):
        powers.append(powers[-1] @ ad)

    for k in range(horizon):
        for ell in range(k + 1):
            block = direct if k == ell else c @ powers[k - ell - 1] @ bd
            lifted[k * p : (k + 1) * p, ell * m : (ell + 1) * m] = block
    return lifted


def finite_horizon_discrete_gramian(
    A_d: ArrayLike,
    B_d: ArrayLike,
    horizon: int,
    input_metric: ArrayLike | None = None,
) -> FloatMatrix:
    """Return the finite-horizon reachability Gramian under an input metric.

    ``input_metric`` is R in ``u.T @ R @ u``; the Gramian uses ``R^{-1}``.
    """

    ad = _as_2d("A_d", A_d)
    bd = _as_2d("B_d", B_d)
    if ad.shape[0] != ad.shape[1] or bd.shape[0] != ad.shape[0]:
        raise ValueError("A_d and B_d have incompatible shapes.")
    if horizon <= 0:
        raise ValueError("horizon must be positive.")

    m = bd.shape[1]
    if input_metric is None:
        r_inv = np.eye(m)
    else:
        r = _as_2d("input_metric", input_metric)
        if r.shape != (m, m):
            raise ValueError("input_metric has incompatible shape.")
        r_inv = np.linalg.inv(r)

    gramian = np.zeros_like(ad)
    power = np.eye(ad.shape[0])
    base = bd @ r_inv @ bd.T
    for _ in range(horizon):
        gramian += power @ base @ power.T
        power = ad @ power
    return gramian


def authority_metrics(
    lifted_map: ArrayLike,
    *,
    common_projection: ArrayLike | None = None,
    differential_projection: ArrayLike | None = None,
    rank_tolerance: float | None = None,
) -> AuthorityMetrics:
    """Compute singular-value and optional projected-output authority metrics."""

    h = _as_2d("lifted_map", lifted_map)
    singular_values = np.linalg.svd(h, compute_uv=False)
    if singular_values.size == 0:
        raise ValueError("lifted_map has no singular values.")
    tolerance = (
        float(rank_tolerance)
        if rank_tolerance is not None
        else max(h.shape) * np.finfo(float).eps * float(singular_values[0])
    )
    nonzero = singular_values[singular_values > tolerance]
    rank = int(nonzero.size)
    minimum = float(nonzero[-1]) if rank else 0.0
    condition = float(nonzero[0] / nonzero[-1]) if rank else math.inf

    def projected_norm(projection: ArrayLike | None) -> float | None:
        if projection is None:
            return None
        p = _as_2d("projection", projection)
        if p.shape[1] != h.shape[0]:
            raise ValueError("Projection must act on the stacked output rows.")
        return float(np.linalg.norm(p @ h, ord=2))

    return AuthorityMetrics(
        singular_values=singular_values,
        spectral_norm=float(singular_values[0]),
        minimum_nonzero_singular_value=minimum,
        numerical_rank=rank,
        condition_number_nonzero=condition,
        projected_common_norm=projected_norm(common_projection),
        projected_differential_norm=projected_norm(differential_projection),
    )


def piecewise_md_decoder_slope(action: ArrayLike, *, at_zero: str = "interval") -> FloatMatrix:
    """Return local normalized-action slopes for the asymmetric direct-M/D decoder.

    At zero the decoder is nonsmooth. ``at_zero='negative'`` returns 200,
    ``'positive'`` returns 600, and ``'interval'`` returns NaN to force the
    caller to perform both one-sided calculations or use [200, 600].
    """

    a = np.asarray(action, dtype=float)
    if not np.isfinite(a).all():
        raise ValueError("action contains non-finite values.")
    slopes = np.where(a > 0.0, 600.0, np.where(a < 0.0, 200.0, np.nan))
    if np.isnan(slopes).any():
        if at_zero == "negative":
            slopes = np.where(np.isnan(slopes), 200.0, slopes)
        elif at_zero == "positive":
            slopes = np.where(np.isnan(slopes), 600.0, slopes)
        elif at_zero != "interval":
            raise ValueError("at_zero must be 'interval', 'negative', or 'positive'.")
    return np.diag(slopes.reshape(-1))


def common_gradient_ratio(
    lambda_value: float,
    grad_q_common: ArrayLike,
    grad_q_differential: ArrayLike,
    *,
    epsilon_floor: float = 1e-12,
) -> float:
    """Return lambda*||grad Qc|| / max(||grad Qd||, floor) in action space."""

    if lambda_value < 0:
        raise ValueError("lambda_value must be nonnegative.")
    gc = np.asarray(grad_q_common, dtype=float).reshape(-1)
    gd = np.asarray(grad_q_differential, dtype=float).reshape(-1)
    if gc.shape != gd.shape:
        raise ValueError("Common and differential action gradients must have equal shape.")
    if not np.isfinite(gc).all() or not np.isfinite(gd).all():
        raise ValueError("Gradients contain non-finite values.")
    return float(lambda_value * np.linalg.norm(gc) / max(np.linalg.norm(gd), epsilon_floor))


def parameter_gradient_ratio(
    lambda_value: float,
    actor_action_jacobian: ArrayLike,
    grad_q_common: ArrayLike,
    grad_q_differential: ArrayLike,
    *,
    epsilon_floor: float = 1e-12,
) -> dict[str, float]:
    """Compare common and differential contributions after the actor Jacobian.

    Returns the norm ratio and cosine. A ratio <= epsilon is the direct test for
    declaring the common term epsilon-negligible on one actor-update sample.
    """

    j = _as_2d("actor_action_jacobian", actor_action_jacobian)
    gc = np.asarray(grad_q_common, dtype=float).reshape(-1)
    gd = np.asarray(grad_q_differential, dtype=float).reshape(-1)
    if j.shape[0] != gc.size or gc.shape != gd.shape:
        raise ValueError("Jacobian rows must match the action-gradient dimension.")

    common = float(lambda_value) * j.T @ gc
    differential = j.T @ gd
    nc = float(np.linalg.norm(common))
    nd = float(np.linalg.norm(differential))
    denom = max(nc * nd, epsilon_floor)
    cosine = float(np.dot(common, differential) / denom)
    return {
        "common_to_differential_norm_ratio": nc / max(nd, epsilon_floor),
        "cosine_between_contributions": cosine,
        "common_norm": nc,
        "differential_norm": nd,
    }


def build_componentwise_slew_matrix(horizon: int, action_dim: int) -> FloatMatrix:
    """Build D such that D @ vec(u) stacks u[0], u[1]-u[0], ... ."""

    if horizon <= 0 or action_dim <= 0:
        raise ValueError("horizon and action_dim must be positive.")
    identity = np.eye(action_dim)
    d = np.zeros((horizon * action_dim, horizon * action_dim), dtype=float)
    for k in range(horizon):
        d[k * action_dim : (k + 1) * action_dim, k * action_dim : (k + 1) * action_dim] = identity
        if k > 0:
            d[k * action_dim : (k + 1) * action_dim, (k - 1) * action_dim : k * action_dim] = -identity
    return d


def required_project_inputs() -> dict[str, list[str]]:
    """Enumerate the matrices/metadata required before authority metrics are evidence."""

    return {
        "per_operating_point_dae": [
            "f_x, f_y, g_x, g_y",
            "f_u and g_u for direct M/D",
            "f_u and g_u for the energy-port command",
            "f_w and g_w for each registered disturbance direction",
            "h_x, h_y, h_u for physical frequency/RoCoF/power outputs",
            "condition number and rank checks for g_y",
        ],
        "actuator_and_estimator": [
            "direct-M/D decoder branch, lower-clamp activity, and normalized slew constraints",
            "energy-port bandpass/estimator state matrices and feasible-headroom mapping derivatives",
            "sample-and-hold timing (0.2 s) and the 30-step/6-s horizon",
        ],
        "comparison_contract": [
            "identical operating points, disturbances, output projections, window, and reference",
            "a common normalized input-energy metric or explicitly reported Pareto frontier",
            "one-sided or constrained finite-difference treatment at the nonsmooth M/D decoder origin",
        ],
    }


if __name__ == "__main__":
    print("This module provides calculation tools; supply actual project Jacobians before drawing plant conclusions.")
    for group, items in required_project_inputs().items():
        print(f"\n{group}:")
        for item in items:
            print(f"  - {item}")
