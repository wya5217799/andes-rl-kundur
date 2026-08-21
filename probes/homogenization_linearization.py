"""Offline homogenization / linear-model math for the R405 gate.

Motivation
----------
The external-solution route (route_successor_design_homogenization.md) claims
that only the zero-state static M/D bias moves the first-order common/differential
cross channel, and that exact decoupling needs [Pc,L]=[Pc,M]=[Pc,D]=0.  This
probe locks the pure offline mathematics behind that claim -- the asymmetric
piecewise action codec, the per-profile homogenization targets, the leading
cross moments, the commutator checks, and the DAE descriptor fold -- so the
ANDES-side runner can reuse verified functions instead of re-deriving them.

Usage
-----
    from probes.homogenization_linearization import homogenization_targets
    t = homogenization_targets([150., 250., 170., 230.], [60., 140., 80., 120.])

Failure modes
-------------
- A profile whose four action boxes have an empty intersection returns
  reachable=False with None targets; callers must branch, never clip silently.
- fold_descriptor reports ok=False (A=None) on a singular or ill-conditioned
  algebraic Jacobian; callers must stop, not substitute.
- All norms are Frobenius-relative; do not mix with spectral norms elsewhere.

This module imports only numpy/scipy -- no ANDES dependency -- so it runs and
is tested on the Windows host.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from scipy.linalg import expm

# Sealed decoder constants (memory/rounds/R401/formal_seal.json
# /contract/decoder; the piecewise application is the V4 env path
# base_env.py: delta = u * max_positive if u >= 0 else u * (-min_negative)).
DELTA_NEGATIVE = -200.0
DELTA_POSITIVE = 600.0
M_FLOOR = 20.0
D_FLOOR = 10.0


def delta_from_normalized(u: float) -> float:
    """Map normalized u in [-1,1] to physical delta via the piecewise codec."""
    u = float(u)
    if not -1.0 <= u <= 1.0:
        raise ValueError(f"normalized action out of box: {u}")
    if u >= 0.0:
        return u * DELTA_POSITIVE
    return u * (-DELTA_NEGATIVE)


def normalized_target_from_delta(delta: float) -> float:
    """Inverse of the piecewise codec: physical delta -> normalized target."""
    delta = float(delta)
    if delta >= 0.0:
        u = delta / DELTA_POSITIVE
    else:
        u = delta / (-DELTA_NEGATIVE)
    if not -1.0 <= u <= 1.0:
        raise ValueError(f"delta outside decodable box: {delta}")
    return u


@dataclass(frozen=True)
class HomogenizationTargets:
    """Static M/D homogenization plan for one profile (candidate A)."""

    reachable: bool
    m_interval: tuple[float, float] | None
    d_interval: tuple[float, float] | None
    m_star: float | None
    d_star: float | None
    normalized_targets: np.ndarray | None


def homogenization_targets(
    M0: Sequence[float],
    D0: Sequence[float],
) -> HomogenizationTargets:
    """Compute candidate-A targets: common (m*, d*) plus normalized 4x2 targets.

    Per profile, every unit may move M within [max(M_FLOOR, M0i+DELTA_NEGATIVE),
    M0i+DELTA_POSITIVE] and D within [max(D_FLOOR, D0i+DELTA_NEGATIVE),
    D0i+DELTA_POSITIVE].  The moment-matched starting point is the harmonic
    mean 1/m* = mean_i 1/M0i and d* = m*^2 mean_i D0i/M0i^2, clipped into the
    common feasible intervals (external solution candidate A).
    """
    m0 = np.asarray(M0, dtype=float)
    d0 = np.asarray(D0, dtype=float)
    if m0.ndim != 1 or d0.ndim != 1 or m0.shape != d0.shape:
        raise ValueError("M0 and D0 must be 1-D sequences of equal length")
    if np.any(m0 <= 0) or np.any(d0 <= 0):
        raise ValueError("M0 and D0 must be strictly positive")

    m_lo = np.maximum(M_FLOOR, m0 + DELTA_NEGATIVE)
    m_hi = m0 + DELTA_POSITIVE
    d_lo = np.maximum(D_FLOOR, d0 + DELTA_NEGATIVE)
    d_hi = d0 + DELTA_POSITIVE

    common_m = (float(np.max(m_lo)), float(np.min(m_hi)))
    common_d = (float(np.max(d_lo)), float(np.min(d_hi)))
    m_ok = common_m[0] <= common_m[1]
    d_ok = common_d[0] <= common_d[1]
    reachable = bool(m_ok and d_ok)
    if not reachable:
        return HomogenizationTargets(
            reachable=False,
            m_interval=common_m if m_ok else None,
            d_interval=common_d if d_ok else None,
            m_star=None,
            d_star=None,
            normalized_targets=None,
        )

    harmonic_m = float(len(m0) / np.sum(1.0 / m0))
    matched_d = float(harmonic_m**2 * np.mean(d0 / (m0**2)))
    m_star = float(np.clip(harmonic_m, common_m[0], common_m[1]))
    d_star = float(np.clip(matched_d, common_d[0], common_d[1]))

    targets = np.empty((m0.size, 2), dtype=float)
    for i in range(m0.size):
        targets[i, 0] = normalized_target_from_delta(m_star - m0[i])
        targets[i, 1] = normalized_target_from_delta(d_star - d0[i])
    return HomogenizationTargets(
        reachable=True,
        m_interval=common_m,
        d_interval=common_d,
        m_star=m_star,
        d_star=d_star,
        normalized_targets=targets,
    )


def common_differential_projectors(
    n: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (q, Pc, Pd) for the arithmetic common/differential split of R^n."""
    if n < 1:
        raise ValueError("n must be positive")
    q = np.ones((n, 1), dtype=float) / np.sqrt(n)
    pc = q @ q.T
    pd = np.eye(n) - pc
    return q, pc, pd


def leading_cross_moments(M: Sequence[float], D: Sequence[float]) -> dict[str, float]:
    """High-frequency cross moments that drive first-order decoupling.

    G(s) = M^-1/s - M^-1 D M^-1/s^2 + O(s^-3); the cross blocks vanish exactly
    when the diagonal quantities are homogeneous in the arithmetic common/
    differential coordinates.  Values:
      variance_inverse_M     = Var_i(1/M_i)
      variance_D_over_M2     = Var_i(D_i/M_i^2)
      projected_inverse_M_norm = ||Pd M^-1 Pc||_F
    """
    mv = np.asarray(M, dtype=float)
    dv = np.asarray(D, dtype=float)
    if mv.ndim != 1 or mv.shape != dv.shape:
        raise ValueError("M and D must be 1-D sequences of equal length")
    if np.any(mv <= 0) or np.any(dv <= 0):
        raise ValueError("M and D must be strictly positive")
    _, _, pd = common_differential_projectors(mv.size)
    _, pc, _ = common_differential_projectors(mv.size)
    minv = np.diag(1.0 / mv)
    projected = pd @ minv @ pc
    return {
        "variance_inverse_M": float(np.var(1.0 / mv)),
        "variance_D_over_M2": float(np.var(dv / (mv**2))),
        "projected_inverse_M_norm": float(np.linalg.norm(projected, "fro")),
    }


def commutator_checks(
    L: np.ndarray,
    M: Sequence[float],
    D: Sequence[float],
) -> dict[str, float]:
    """Relative Frobenius checks for the exact-decoupling theorem.

    Exact arithmetic common/differential decoupling requires
    [Pc,L]=[Pc,M]=[Pc,D]=0 (and balanced L1 = 1^T L = 0).  All entries are
    relative to the operand's own Frobenius norm (floor 1.0), so a 0.0 means
    exact satisfaction and 1e-2 means one-percent-level residual.
    """
    L = np.asarray(L, dtype=float)
    mv = np.asarray(M, dtype=float)
    dv = np.asarray(D, dtype=float)
    n = mv.size
    if L.shape != (n, n):
        raise ValueError("L must be n x n for n units")
    _, pc, _ = common_differential_projectors(n)
    one = np.ones(n)

    def rel_norm(x: np.ndarray, scale: np.ndarray) -> float:
        # Raveled 2-norm equals the Frobenius norm for matrices and the
        # Euclidean norm for 1-D balance vectors.
        return float(
            np.linalg.norm(np.ravel(x)) / max(1.0, np.linalg.norm(np.ravel(scale)))
        )

    mm = np.diag(mv)
    dm = np.diag(dv)
    return {
        "L_right_balance": rel_norm(L @ one, L),
        "L_left_balance": rel_norm(one @ L, L),
        "commutator_L": rel_norm(pc @ L - L @ pc, L),
        "commutator_M": rel_norm(pc @ mm - mm @ pc, mm),
        "commutator_D": rel_norm(pc @ dm - dm @ pc, dm),
    }


def fold_descriptor(
    f_x: np.ndarray,
    f_y: np.ndarray,
    g_x: np.ndarray,
    g_y: np.ndarray,
) -> dict[str, object]:
    """Fold a DAE descriptor to A = f_x - f_y g_y^-1 g_x with checks.

    Returns {"ok": bool, "A": ndarray|None, "g_y_condition": float,
    "finite": bool}.  A singular or NaN-polluted algebraic Jacobian returns
    ok=False and A=None; callers must treat that as a failure, not repair it.
    """
    f_x = np.asarray(f_x, dtype=float)
    f_y = np.asarray(f_y, dtype=float)
    g_x = np.asarray(g_x, dtype=float)
    g_y = np.asarray(g_y, dtype=float)
    if f_x.ndim != 2 or f_y.ndim != 2 or g_x.ndim != 2 or g_y.ndim != 2:
        raise ValueError("all descriptor blocks must be 2-D")
    if f_x.shape[0] != f_x.shape[1] or f_y.shape[0] != f_x.shape[0]:
        raise ValueError("f_x/f_y state dimensions mismatch")
    if g_y.shape[0] != g_y.shape[1] or g_y.shape[0] != g_x.shape[0]:
        raise ValueError("g_y/g_x algebraic dimensions mismatch")
    if f_y.shape[1] != g_y.shape[0] or g_x.shape[1] != f_x.shape[1]:
        raise ValueError("descriptor block shapes do not compose")

    if not np.all(np.isfinite(f_x)) or not np.all(np.isfinite(f_y)) or not np.all(
        np.isfinite(g_x)
    ) or not np.all(np.isfinite(g_y)):
        return {"ok": False, "A": None, "g_y_condition": float("nan"), "finite": False}

    cond = float(np.linalg.cond(g_y))
    try:
        g_y_inv = np.linalg.inv(g_y)
    except np.linalg.LinAlgError:
        return {"ok": False, "A": None, "g_y_condition": cond, "finite": True}

    a = f_x - f_y @ g_y_inv @ g_x
    if not np.all(np.isfinite(a)):
        return {"ok": False, "A": None, "g_y_condition": cond, "finite": False}
    return {"ok": True, "A": a, "g_y_condition": cond, "finite": True}

# Registered arithmetic differential transform (memory/rounds/R401/
# formal_seal.json /contract/differential_transform).  Rows are orthonormal
# and orthogonal to 1, so z_d energy numbers are basis-independent.
REGISTERED_DIFFERENTIAL_TRANSFORM = np.array(
    [
        [0.5, 0.5, -0.5, -0.5],
        [0.7071067811865475, -0.7071067811865475, 0.0, 0.0],
        [0.0, 0.0, 0.7071067811865475, -0.7071067811865475],
    ],
    dtype=float,
)

SLEW_LIMIT = 0.25


def homogenized_action_schedule(
    targets: np.ndarray,
    *,
    steps: int = 30,
    slew: float = SLEW_LIMIT,
) -> np.ndarray:
    """Deterministic slew-ramped candidate-A action schedule (steps, n, 2).

    Starts from zero action and moves each coordinate toward its target by at
    most 'slew' per step, then holds.  This is the offline reference for the
    runtime LocalMDActionProjector path; the runner must reproduce it exactly
    on every recorded trajectory.
    """
    targets = np.asarray(targets, dtype=float)
    if targets.ndim != 2 or targets.shape[1] != 2:
        raise ValueError("targets must have shape (n_units, 2)")
    if np.any(~np.isfinite(targets)) or np.any(np.abs(targets) > 1.0):
        raise ValueError("targets must be finite and inside [-1, 1]")
    if steps < 1 or slew <= 0.0:
        raise ValueError("steps must be positive and slew strictly positive")

    schedule = np.zeros((steps, targets.shape[0], 2), dtype=float)
    current = np.zeros_like(targets)
    for k in range(steps):
        current = current + np.clip(targets - current, -slew, slew)
        schedule[k] = current
    return schedule


def reduced_swing_matrices(
    L: np.ndarray, M: list[float] | np.ndarray, D: list[float] | np.ndarray,
    omega_n: float = 2.0 * np.pi * 60.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduced 4-unit swing A and B (single home; shared with the src fold)."""
    mv = np.asarray(M, dtype=float)
    dv = np.asarray(D, dtype=float)
    minv = np.diag(1.0 / mv)
    a = np.block([
        [np.zeros((mv.size, mv.size)), omega_n * np.eye(mv.size)],
        [-minv @ np.asarray(L, dtype=float), -minv @ np.diag(dv)],
    ])
    b = np.vstack([np.zeros((mv.size, mv.size)), minv])
    return a, b


def zoh_discretize(a: np.ndarray, b: np.ndarray, dt: float) -> tuple[np.ndarray, np.ndarray]:
    """Zero-order-hold discretization of (A, B) over one sample period."""
    n, m = b.shape
    aug = np.block([[a, b], [np.zeros((m, n + m))]])
    e = expm(aug * dt)
    return e[:n, :n], e[:n, n:]


def linear_cross_energy(
    L: np.ndarray,
    M: list[float] | np.ndarray,
    D: list[float] | np.ndarray,
    common_probes: list[np.ndarray],
    differential_probes: list[np.ndarray],
    *,
    dt: float = 0.2,
    omega_n: float = 2.0 * np.pi * 60.0,
    transform: np.ndarray | None = None,
) -> dict[str, float]:
    """Frozen linear-model cross energies under the registered transform.

    Simulates the reduced 4-unit swing model with zero-order-held injections
    w (shape (steps, n)) and returns
      E_d_from_c = sum over common probes of dt * ||z_d||^2,
      E_c_from_d = sum over differential probes of dt * z_c^2,
      E_cross    = E_d_from_c + E_c_from_d,
    with z_c = mean_i omega_i and z_d = transform @ omega (registered T_d by
    default).  The reduced injection vector w models the net power unbalance
    at the four VSG buses after network reduction; it is an analysis-tool
    model, not the ANDES DAE itself.
    """
    td = (
        REGISTERED_DIFFERENTIAL_TRANSFORM
        if transform is None
        else np.asarray(transform, dtype=float)
    )
    n = len(M)
    if td.shape != (n - 1, n):
        raise ValueError("transform must have shape (n-1, n)")
    if not np.allclose(td @ np.ones(n), np.zeros(n - 1), atol=1e-9):
        raise ValueError("transform rows must lie in 1^perp")

    a, b = reduced_swing_matrices(L, M, D, omega_n)
    ad, bd = zoh_discretize(a, b, dt)
    e_dc = 0.0
    e_cd = 0.0
    for w in common_probes:
        w = np.asarray(w, dtype=float)
        if w.ndim != 2 or w.shape[1] != n:
            raise ValueError("probe waveforms must have shape (steps, n)")
        x = np.zeros(2 * n)
        for wk in w:
            x = ad @ x + bd @ wk
        omega = x[n:]
        zd = td @ omega
        e_dc += float(dt * np.sum(zd * zd))
    for w in differential_probes:
        w = np.asarray(w, dtype=float)
        if w.ndim != 2 or w.shape[1] != n:
            raise ValueError("probe waveforms must have shape (steps, n)")
        x = np.zeros(2 * n)
        for wk in w:
            x = ad @ x + bd @ wk
        omega = x[n:]
        zc = float(np.mean(omega))
        e_cd += float(dt * zc * zc)
    return {"E_d_from_c": e_dc, "E_c_from_d": e_cd, "E_cross": e_dc + e_cd}

def kron_reduce_b_block(
    b_full: np.ndarray,
    vsg_indices: list[int],
) -> np.ndarray:
    """Kron-reduce a network B-block to the VSG buses.

    Given the full bus susceptance block B = d p_e / d theta (rows and columns
    ordered by bus), eliminate every non-VSG bus via the Schur complement
    L = B_vv - B_vl B_ll^-1 B_lv.  For a lossless connected network this is
    exactly the reduced Laplacian seen by the VSG swing equations.
    """
    b_full = np.asarray(b_full, dtype=float)
    if b_full.ndim != 2 or b_full.shape[0] != b_full.shape[1]:
        raise ValueError("b_full must be square")
    vsg = sorted(int(i) for i in vsg_indices)
    if not vsg or len(set(vsg)) != len(vsg):
        raise ValueError("vsg_indices must be non-empty and unique")
    if max(vsg) >= b_full.shape[0]:
        raise ValueError("vsg_indices out of range")
    load = [i for i in range(b_full.shape[0]) if i not in vsg]
    if not load:
        return b_full[np.ix_(vsg, vsg)].copy()
    b_vv = b_full[np.ix_(vsg, vsg)]
    b_vl = b_full[np.ix_(vsg, load)]
    b_ll = b_full[np.ix_(load, load)]
    b_lv = b_full[np.ix_(load, vsg)]
    try:
        b_ll_inv = np.linalg.inv(b_ll)
    except np.linalg.LinAlgError as exc:
        raise ValueError("load-bus B-block is singular; cannot reduce") from exc
    return b_vv - b_vl @ b_ll_inv @ b_lv


def check_reduced_l(
    l_red: np.ndarray,
    *,
    tolerance: float = 1e-8,
) -> dict[str, object]:
    """Structural sanity checks for an extracted reduced Laplacian.

    A valid lossless reduced L must be symmetric, balanced (L1 = 1^T L = 0),
    and have nonnegative real eigenvalues.  ok=False means the extraction is
    unreliable and must not feed downstream analysis.
    """
    l_red = np.asarray(l_red, dtype=float)
    if l_red.ndim != 2 or l_red.shape[0] != l_red.shape[1]:
        raise ValueError("l_red must be square")
    one = np.ones(l_red.shape[0])
    symmetric = bool(np.allclose(l_red, l_red.T, atol=tolerance, rtol=tolerance))
    right_balance = float(np.linalg.norm(l_red @ one))
    left_balance = float(np.linalg.norm(one @ l_red))
    eig = np.linalg.eigvalsh((l_red + l_red.T) / 2.0)
    psd = bool(np.all(eig >= -tolerance))
    ok = bool(
        symmetric
        and right_balance <= tolerance
        and left_balance <= tolerance
        and psd
    )
    return {
        "ok": ok,
        "symmetric": symmetric,
        "right_balance": right_balance,
        "left_balance": left_balance,
        "min_eigenvalue": float(np.min(eig)),
    }
