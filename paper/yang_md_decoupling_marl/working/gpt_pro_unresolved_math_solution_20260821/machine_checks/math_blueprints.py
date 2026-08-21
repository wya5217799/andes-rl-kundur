"""Generic numerical blueprints used by the U1--U9 report.

These routines are intentionally plant-agnostic. They do not reconstruct the omitted Object-B
matrices. They provide independently testable implementations for the algebraic formulas once
those matrices are exported.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.linalg import expm
from scipy.optimize import linear_sum_assignment

ComplexArray = NDArray[np.complex128]
FloatArray = NDArray[np.float64]


def projector_common(n: int) -> FloatArray:
    if n <= 0:
        raise ValueError("n must be positive")
    q = np.ones((n, 1), dtype=float) / np.sqrt(float(n))
    return q @ q.T


def project_slew(previous: ArrayLike, raw: ArrayLike, slew_limit: float) -> FloatArray:
    previous_a = np.clip(np.asarray(previous, dtype=float), -1.0, 1.0)
    raw_a = np.clip(np.asarray(raw, dtype=float), -1.0, 1.0)
    if previous_a.shape != raw_a.shape:
        raise ValueError("previous and raw actions must have equal shape")
    if not np.isfinite(slew_limit) or not (0.0 < slew_limit <= 2.0):
        raise ValueError("slew_limit must lie in (0, 2]")
    delta = np.clip(raw_a - previous_a, -slew_limit, slew_limit)
    return np.clip(previous_a + delta, -1.0, 1.0)


def zoh_integral(a: ArrayLike, b: ArrayLike, horizon: float) -> FloatArray:
    """Return integral_0^h exp(A r) B dr without inverting A."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1]:
        raise ValueError("A must be square")
    if b.ndim != 2 or b.shape[0] != a.shape[0]:
        raise ValueError("B row dimension must match A")
    if horizon < 0:
        raise ValueError("horizon must be nonnegative")
    n, m = b.shape
    block = np.block(
        [
            [a, b],
            [np.zeros((m, n)), np.zeros((m, m))],
        ]
    )
    return expm(block * float(horizon))[:n, n:]


def fractional_zoh_split(
    a_c: ArrayLike, b_c: ArrayLike, sample_period: float, fractional_delay: float
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Exact ZOH split for tau=mT+delta within one sample interval.

    Returns (A_d, B0, B1), where
      x[k+1] = A_d x[k] + B0 u[k-m] + B1 u[k-m-1].
    """
    if sample_period <= 0:
        raise ValueError("sample_period must be positive")
    delta = float(fractional_delay)
    if not (0.0 <= delta < sample_period + 1e-15):
        raise ValueError("fractional_delay must lie in [0, sample_period]")
    delta = min(delta, sample_period)
    a_c = np.asarray(a_c, dtype=float)
    b_c = np.asarray(b_c, dtype=float)
    a_d = expm(a_c * sample_period)
    full = zoh_integral(a_c, b_c, sample_period)
    b0 = zoh_integral(a_c, b_c, sample_period - delta)
    b1 = full - b0
    return a_d, b0, b1


@dataclass(frozen=True)
class TransferSensitivity:
    pc: ComplexArray
    pw: ComplexArray
    g: ComplexArray
    pc_rho: ComplexArray
    pw_rho: ComplexArray
    g_rho: ComplexArray


def closed_loop_transfer_sensitivity(
    *,
    z: complex,
    a: ArrayLike,
    b_c: ArrayLike,
    b_w: ArrayLike,
    c: ArrayLike,
    d_c: ArrayLike,
    d_w: ArrayLike,
    k: ArrayLike,
    a_rho: ArrayLike,
    b_c_rho: ArrayLike,
    b_w_rho: ArrayLike,
    c_rho: ArrayLike,
    d_c_rho: ArrayLike,
    d_w_rho: ArrayLike,
    k_rho: ArrayLike,
) -> TransferSensitivity:
    """Evaluate G=S Pw and its exact total derivative at one discrete frequency."""
    a = np.asarray(a, dtype=complex)
    b_c = np.asarray(b_c, dtype=complex)
    b_w = np.asarray(b_w, dtype=complex)
    c = np.asarray(c, dtype=complex)
    d_c = np.asarray(d_c, dtype=complex)
    d_w = np.asarray(d_w, dtype=complex)
    k = np.asarray(k, dtype=complex)
    a_rho = np.asarray(a_rho, dtype=complex)
    b_c_rho = np.asarray(b_c_rho, dtype=complex)
    b_w_rho = np.asarray(b_w_rho, dtype=complex)
    c_rho = np.asarray(c_rho, dtype=complex)
    d_c_rho = np.asarray(d_c_rho, dtype=complex)
    d_w_rho = np.asarray(d_w_rho, dtype=complex)
    k_rho = np.asarray(k_rho, dtype=complex)

    resolvent_matrix = z * np.eye(a.shape[0], dtype=complex) - a
    xc = np.linalg.solve(resolvent_matrix, b_c)
    xw = np.linalg.solve(resolvent_matrix, b_w)
    pc = c @ xc + d_c
    pw = c @ xw + d_w

    xc_rho = np.linalg.solve(resolvent_matrix, a_rho @ xc + b_c_rho)
    xw_rho = np.linalg.solve(resolvent_matrix, a_rho @ xw + b_w_rho)
    pc_rho = c_rho @ xc + c @ xc_rho + d_c_rho
    pw_rho = c_rho @ xw + c @ xw_rho + d_w_rho

    return_matrix = np.eye(pc.shape[0], dtype=complex) + pc @ k
    g = np.linalg.solve(return_matrix, pw)
    l_rho = pc_rho @ k + pc @ k_rho
    g_rho = np.linalg.solve(return_matrix, pw_rho - l_rho @ g)
    return TransferSensitivity(pc, pw, g, pc_rho, pw_rho, g_rho)


def finite_band_energy(
    transfers: Iterable[ArrayLike], weights: Iterable[float]
) -> float:
    total = 0.0
    for g, weight in zip(transfers, weights, strict=True):
        matrix = np.asarray(g, dtype=complex)
        total += float(weight) * float(np.vdot(matrix, matrix).real)
    return total


def finite_band_energy_derivative(
    transfers: Iterable[ArrayLike], derivatives: Iterable[ArrayLike], weights: Iterable[float]
) -> float:
    total = 0.0
    for g, dg, weight in zip(transfers, derivatives, weights, strict=True):
        g_a = np.asarray(g, dtype=complex)
        dg_a = np.asarray(dg, dtype=complex)
        total += 2.0 * float(weight) * float(np.vdot(g_a, dg_a).real)
    return total


def mixed_partial_vector(
    reduced_field: Callable[[FloatArray, FloatArray, FloatArray], FloatArray],
    *,
    state_direction: ArrayLike,
    action_index: int,
    state_step: float,
    action_step: float,
    action_dim: int,
    disturbance_dim: int = 0,
) -> FloatArray:
    """Central four-corner estimate of d^2 f / dx du_j applied to a direction."""
    v = np.asarray(state_direction, dtype=float)
    e = np.zeros(action_dim, dtype=float)
    e[action_index] = 1.0
    w = np.zeros(disturbance_dim, dtype=float)
    hp = float(state_step) * v
    up = float(action_step) * e
    return (
        reduced_field(hp, up, w)
        - reduced_field(hp, -up, w)
        - reduced_field(-hp, up, w)
        + reduced_field(-hp, -up, w)
    ) / (4.0 * float(state_step) * float(action_step))


def commutator(a: ArrayLike, p: ArrayLike) -> ComplexArray:
    a = np.asarray(a, dtype=complex)
    p = np.asarray(p, dtype=complex)
    return a @ p - p @ a


def resolvent_commutator_identity(
    a: ArrayLike, p: ArrayLike, s: complex
) -> tuple[ComplexArray, ComplexArray]:
    a = np.asarray(a, dtype=complex)
    p = np.asarray(p, dtype=complex)
    r = np.linalg.inv(s * np.eye(a.shape[0], dtype=complex) - a)
    left = r @ p - p @ r
    right = r @ commutator(a, p) @ r
    return left, right


def match_eigenvalue_branches(
    previous: ArrayLike, current: ArrayLike
) -> NDArray[np.int64]:
    """Match eigenvalues by minimum total Euclidean distance (basic continuation helper)."""
    prev = np.asarray(previous, dtype=complex).reshape(-1)
    cur = np.asarray(current, dtype=complex).reshape(-1)
    if prev.size != cur.size:
        raise ValueError("previous and current must have equal size")
    cost = np.abs(prev[:, None] - cur[None, :])
    rows, cols = linear_sum_assignment(cost)
    order = np.empty_like(cols)
    order[rows] = cols
    return order.astype(np.int64)
