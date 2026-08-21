"""Linear-model construction and folded-LTI analysis for R405.

Motivation
----------
R405 archives a numerical linearization of the ANDES four-VSG model at each
canary profile operating point and evaluates the first-order cross channel on
the frozen model.  The pure linear-algebra parts live here so they can be
tested on the Windows host; the ANDES-coupled snapshotting lives in the WSL
runner (scripts/run_r405_homogenization_gate.py).

Usage
-----
    A, B = reduced_swing_matrices(L, M, D, omega_n)
    out = folded_linear_probe_energy(A, B, C, common_probes, differential_probes)

Failure modes
-------------
- fold_input_columns raises on a singular algebraic Jacobian; callers must
  stop, never substitute.
- folded_linear_probe_energy validates shapes and the 1^perp property of the
  transform before simulating.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
from probes.homogenization_linearization import (
    REGISTERED_DIFFERENTIAL_TRANSFORM,
    check_reduced_l,
    fold_descriptor,
    kron_reduce_b_block,
    reduced_swing_matrices,
    zoh_discretize,
)


def fold_input_columns(
    f_u: np.ndarray,
    g_u: np.ndarray,
    f_y: np.ndarray,
    g_y: np.ndarray,
) -> np.ndarray:
    """Fold input Jacobians: B = f_u - f_y g_y^-1 g_u."""
    f_u = np.asarray(f_u, dtype=float)
    g_u = np.asarray(g_u, dtype=float)
    # ANDES residual vectors arrive flat; a single input column is one vector.
    if f_u.ndim == 1:
        f_u = f_u.reshape(-1, 1)
    if g_u.ndim == 1:
        g_u = g_u.reshape(-1, 1)
    f_y = np.asarray(f_y, dtype=float)
    g_y = np.asarray(g_y, dtype=float)
    if f_u.ndim != 2 or g_u.ndim != 2:
        raise ValueError("f_u and g_u must be 2-D")
    if f_u.shape[0] != f_y.shape[0] or g_u.shape[0] != g_y.shape[0]:
        raise ValueError("input column rows must match descriptor rows")
    if f_u.shape[1] != g_u.shape[1]:
        raise ValueError("f_u and g_u must share the same column count")
    if g_y.shape[0] != g_y.shape[1] or f_y.shape[1] != g_y.shape[0]:
        raise ValueError("algebraic Jacobian shapes must compose")
    try:
        g_y_inv = np.linalg.inv(g_y)
    except np.linalg.LinAlgError as exc:
        raise ValueError("algebraic Jacobian is singular") from exc
    b = f_u - f_y @ g_y_inv @ g_u
    if not np.all(np.isfinite(b)):
        raise ValueError("folded input columns contain nonfinite values")
    return b


def folded_linear_probe_energy(
    a: np.ndarray,
    b: np.ndarray,
    c: np.ndarray,
    common_probes: list[np.ndarray],
    differential_probes: list[np.ndarray],
    *,
    dt: float,
    transform: np.ndarray | None = None,
) -> dict[str, float]:
    """Cross energies of a folded LTI model under registered probe waveforms.

    A is n x n, B is n x m, C is 4 x n (frequency rows).  Waveforms are
    (steps, m) zero-order-held injections.  Returns E_d_from_c, E_c_from_d,
    E_cross under the registered arithmetic transform.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or b.shape[0] != a.shape[0]:
        raise ValueError("A/B shape mismatch")
    if c.ndim != 2 or c.shape[1] != a.shape[0] or c.shape[0] != 4:
        raise ValueError("C must be 4 x n")
    td = (
        REGISTERED_DIFFERENTIAL_TRANSFORM
        if transform is None
        else np.asarray(transform, dtype=float)
    )
    if td.shape != (3, 4) or not np.allclose(td @ np.ones(4), np.zeros(3), atol=1e-9):
        raise ValueError("transform must be 3 x 4 with rows in 1^perp")

    n, m = b.shape
    ad, bd = zoh_discretize(a, b, dt)
    e_dc = 0.0
    e_cd = 0.0
    for w in common_probes:
        w = np.asarray(w, dtype=float)
        if w.ndim != 2 or w.shape[1] != m:
            raise ValueError("probe waveforms must have shape (steps, m)")
        x = np.zeros(n)
        for wk in w:
            x = ad @ x + bd @ wk
        omega = c @ x
        zd = td @ omega
        e_dc += float(dt * np.sum(zd * zd))
    for w in differential_probes:
        w = np.asarray(w, dtype=float)
        if w.ndim != 2 or w.shape[1] != m:
            raise ValueError("probe waveforms must have shape (steps, m)")
        x = np.zeros(n)
        for wk in w:
            x = ad @ x + bd @ wk
        omega = c @ x
        zc = float(np.mean(omega))
        e_cd += float(dt * zc * zc)
    return {"E_d_from_c": e_dc, "E_c_from_d": e_cd, "E_cross": e_dc + e_cd}


def fold_with_e(
    e_diag: np.ndarray,
    f_x: np.ndarray,
    f_algebraic: np.ndarray,
    g_x: np.ndarray,
    g_algebraic: np.ndarray,
) -> dict[str, object]:
    """E-weighted Schur fold: A = E^-1 (f_x - f_algebraic g_algebraic^-1 g_x).

    Used on the zero-time-constant FoldedDescriptor from the model-first
    bridge, whose dynamic part is scaled by diag(Tf).  Returns the same
    {"ok", "A", "g_y_condition", "finite"} shape as fold_descriptor.
    """
    e_diag = np.asarray(e_diag, dtype=float)
    if e_diag.ndim == 2 and e_diag.shape[0] == e_diag.shape[1]:
        # The model-first bridge stores e_d as np.diag(...); take the diagonal.
        e_diag = np.diag(e_diag)
    f_x = np.asarray(f_x, dtype=float)
    f_algebraic = np.asarray(f_algebraic, dtype=float)
    g_x = np.asarray(g_x, dtype=float)
    g_algebraic = np.asarray(g_algebraic, dtype=float)
    if e_diag.ndim != 1 or np.any(e_diag <= 0) or not np.all(np.isfinite(e_diag)):
        raise ValueError("e_diag must be a finite positive vector")
    if f_x.shape[0] != f_x.shape[1] or f_x.shape[0] != e_diag.size:
        raise ValueError("f_x/e_diag dimension mismatch")
    if f_algebraic.shape[0] != f_x.shape[0] or g_algebraic.shape[0] != g_algebraic.shape[1]:
        raise ValueError("algebraic block shapes must compose")
    if f_algebraic.shape[1] != g_algebraic.shape[0] or g_x.shape[0] != g_algebraic.shape[0]:
        raise ValueError("descriptor blocks do not compose")
    if g_x.shape[1] != f_x.shape[1]:
        raise ValueError("g_x column count mismatch")
    if not all(
        np.all(np.isfinite(m))
        for m in (e_diag, f_x, f_algebraic, g_x, g_algebraic)
    ):
        return {"ok": False, "A": None, "g_y_condition": float("nan"), "finite": False}
    cond = float(np.linalg.cond(g_algebraic))
    try:
        g_inv = np.linalg.inv(g_algebraic)
    except np.linalg.LinAlgError:
        return {"ok": False, "A": None, "g_y_condition": cond, "finite": True}
    a = (f_x - f_algebraic @ g_inv @ g_x) / e_diag[:, None]
    if not np.all(np.isfinite(a)):
        return {"ok": False, "A": None, "g_y_condition": cond, "finite": False}
    return {"ok": True, "A": a, "g_y_condition": cond, "finite": True}

def dense_matrix(values: object) -> np.ndarray:
    """Dense copy of an ANDES/kvxopt/scipy sparse Jacobian block."""
    matrix = np.asarray(values)
    if hasattr(matrix, "todense"):
        matrix = np.asarray(matrix.todense())
    elif hasattr(values, "V") and hasattr(values, "size"):
        rows, cols = values.size
        dense = np.zeros((rows, cols), dtype=float)
        dense[np.asarray(values.I, dtype=int), np.asarray(values.J, dtype=int)] = (
            np.asarray(values.V, dtype=float)
        )
        matrix = dense
    return np.asarray(matrix, dtype=float)


def snapshot_profile_jacobians(env: object, profile_id: str) -> dict[str, object]:
    """Fold and validate the DAE Jacobians at one initialized profile point.

    Uses the zero-time-constant pipeline fold (R380 machinery) as the
    validated descriptor; the raw Schur fold's positive-real pairs are
    reported as reduction artifacts under the ill-conditioned g_y.
    """
    from andes_rl_kundur.evaluation.model_first_input_bridge import (
        fold_zero_time_constant_states,
    )

    system = env.ss
    models = system.exist.pflow_tds
    system.TDS.fg_update(models=models)
    system.j_update(models=models, info="R405 profile linearization")
    fx = dense_matrix(system.dae.fx)
    fy = dense_matrix(system.dae.fy)
    gx = dense_matrix(system.dae.gx)
    gy = dense_matrix(system.dae.gy)
    f_res = np.asarray(system.dae.f, dtype=float)
    g_res = np.asarray(system.dae.g, dtype=float)
    init_residual_pass = bool(
        float(np.max(np.abs(f_res))) <= 1e-4
        and float(np.max(np.abs(g_res))) <= 1e-4
    )
    fold = fold_descriptor(fx, fy, gx, gy)
    eig_real = np.real(np.linalg.eigvals(fold["A"])) if fold["ok"] else np.array([])
    positive_real_count = int(np.sum(eig_real > 1e-7)) if fold["ok"] else -1
    e_fold_ok = False
    e_fold_positive_real = -1
    e_fold_dynamic = 0
    try:
        tf = np.asarray(system.dae.Tf, dtype=float)
        descriptor = fold_zero_time_constant_states(
            time_constants=tf,
            f_x=fx,
            f_y=fy,
            g_x=gx,
            g_y=gy,
            f_input=np.zeros((fx.shape[0], 0)),
            g_input=np.zeros((gy.shape[0], 0)),
        )
        e_fold = fold_with_e(
            np.asarray(descriptor.e_d, dtype=float),
            np.asarray(descriptor.f_x, dtype=float),
            np.asarray(descriptor.f_algebraic, dtype=float),
            np.asarray(descriptor.g_x, dtype=float),
            np.asarray(descriptor.g_algebraic, dtype=float),
        )
        e_fold_ok = bool(e_fold["ok"])
        if e_fold_ok:
            e_eig = np.real(np.linalg.eigvals(e_fold["A"]))
            e_fold_positive_real = int(np.sum(e_eig > 1e-7))
            e_fold_dynamic = int(np.asarray(descriptor.e_d).shape[0])
    except (ValueError, AttributeError, KeyError):
        e_fold_ok = False
    return {
        "profile_id": profile_id,
        "fold_ok": bool(fold["ok"]),
        "g_y_condition": fold["g_y_condition"],
        "initialization_max_abs_f": float(np.max(np.abs(f_res))),
        "initialization_max_abs_g": float(np.max(np.abs(g_res))),
        "init_residual_pass": init_residual_pass,
        "positive_real_count": positive_real_count,
        "e_fold_ok": e_fold_ok,
        "e_fold_positive_real_count": e_fold_positive_real,
        "e_fold_dynamic_state_count": e_fold_dynamic,
        "state_dim": int(fx.shape[0]),
        "algebraic_dim": int(gy.shape[0]),
    }


def load_input_columns(
    env: object,
    *,
    perturbed_env_factory: object,
    load_ids: Sequence[str],
    eps_steps: Sequence[float],
) -> dict[str, object]:
    """Finite-difference load input columns folded through the base Jacobians.

    Each column is evaluated at the base equilibrium point (x0, y0) on a
    freshly built perturbed system; two eps steps report the relative column
    drift as a fidelity signal.
    """
    system = env.ss
    fy = dense_matrix(system.dae.fy)
    gy = dense_matrix(system.dae.gy)
    x0 = np.asarray(system.dae.x, dtype=float).copy()
    y0 = np.asarray(system.dae.y, dtype=float).copy()
    columns: dict[str, object] = {}
    for load_id in load_ids:
        per_step: list[dict[str, object]] = []
        previous: np.ndarray | None = None
        for eps in eps_steps:
            perturbed = perturbed_env_factory()
            perturbed.reset(delta_u={load_id: eps})
            perturbed.ss.dae.x[:] = x0
            perturbed.ss.dae.y[:] = y0
            models = perturbed.ss.exist.pflow_tds
            perturbed.ss.TDS.fg_update(models=models)
            f_res = np.asarray(perturbed.ss.dae.f, dtype=float)
            g_res = np.asarray(perturbed.ss.dae.g, dtype=float)
            b_col = fold_input_columns(f_res / eps, g_res / eps, fy, gy)
            column_diff = None
            if previous is not None:
                column_diff = float(
                    np.linalg.norm(b_col[:, 0] - previous[:, 0])
                    / max(np.linalg.norm(previous[:, 0]), 1e-12)
                )
            previous = b_col
            per_step.append({"eps": eps, "column_diff_vs_previous": column_diff})
        columns[str(load_id)] = {
            "steps": per_step,
            "final_column_finite": bool(np.all(np.isfinite(previous))),
        }
    return columns


def try_extract_reduced_l(env: object) -> dict[str, object]:
    """Best-effort reduced 4x4 L via PFlow.B + Kron reduction, honest otherwise."""
    try:
        b_full = dense_matrix(env.ss.PFlow.B)
    except AttributeError:
        return {"extracted": False, "reason": "PFlow.B not available"}
    vsg_buses = sorted({int(env.ss.GENCLS.bus.v[pos]) for pos in env._vsg_pos})
    all_buses = sorted({int(bus) for bus in env.ss.Bus.idx.v})
    if set(vsg_buses) - set(all_buses):
        return {"extracted": False, "reason": "vsg bus index mismatch"}
    vsg_positions = [all_buses.index(bus) for bus in vsg_buses]
    if b_full.shape != (len(all_buses), len(all_buses)):
        return {
            "extracted": False,
            "reason": f"PFlow.B shape {b_full.shape} != bus count {len(all_buses)}",
        }
    l_red = kron_reduce_b_block(b_full, vsg_positions)
    checks = check_reduced_l(l_red)
    return {"extracted": True, "vsg_buses": vsg_buses, "checks": checks}
