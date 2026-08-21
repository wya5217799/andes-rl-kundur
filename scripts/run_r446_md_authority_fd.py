"""R446 — DAE first-order authority B_{u,r} finite-difference measurement (Object A).

Motivation: the VSG failure-math advisory (P3) left "the actual ANDES B_{u,r}
unresolved". An offline code-structure analysis predicted B_{u,r}=0 at the
synchronous power-balanced equilibrium. This runner seals that prediction
numerically by the advisory's recipe: freeze the equilibrium (x*, y*), finite-
difference the M/D input columns f_u, g_u, and Schur-fold them into
B_{u,r} = f_u - f_y g_y^-1 g_u.

Run via the WSL scratch launcher (ANDES = WSL only):
    python scripts/andes_scratch.py scripts/run_r446_md_authority_fd.py rehearse
    python scripts/andes_scratch.py scripts/run_r446_md_authority_fd.py analyse

rehearse: one column (DeltaM_1) at h=1e-3, no formal result written.
analyse : full 8-column x geometric-h measurement, writes
    results/research_loop/r446_md_authority_fd/formal_analysis.json (+.sha256).

Failure modes: env build / fg_update / j_update failure -> exit 2 (rehearse
should catch before analyse). Singular g_y or a non-equilibrium point ->
CANARY-INVALID verdict (not a crash).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
for _bootstrap_path in (ROOT, ROOT / "src"):
    if str(_bootstrap_path) not in sys.path:
        sys.path.insert(0, str(_bootstrap_path))
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
):
    os.environ[_thread_variable] = "1"
os.environ["DISABLE_TOGGLER"] = "1"

OUT = ROOT / "results" / "research_loop" / "r446_md_authority_fd"
H_GRID = (1e-2, 1e-3, 1e-4)
MATERIALITY = 1e-6
GY_COND_LIMIT = 1e10
EQ_GATE = 1e-6


def _build_env():
    from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4

    env = AndesMultiVSGEnvV4(
        random_disturbance=False,
        comm_fail_prob=0.0,
        comm_delay_steps=0,
    )
    return env


def _snapshot(env):
    """Return the frozen-equilibrium snapshot and the dense f_y, g_y."""
    from andes_rl_kundur.evaluation.r405_linearization import dense_matrix

    ss = env.ss
    models = ss.exist.pflow_tds
    ss.TDS.fg_update(models=models)
    ss.j_update(models=models, info="R446 equilibrium linearization")
    fy = dense_matrix(ss.dae.fy)
    gy = dense_matrix(ss.dae.gy)
    f_res = np.asarray(ss.dae.f, dtype=float)
    g_res = np.asarray(ss.dae.g, dtype=float)
    vsg_pos = list(env._vsg_pos)
    omega = np.asarray([ss.GENCLS.omega.v[p] for p in vsg_pos], dtype=float)
    m_base = np.asarray([ss.GENCLS.M.v[p] for p in vsg_pos], dtype=float)
    d_base = np.asarray([ss.GENCLS.D.v[p] for p in vsg_pos], dtype=float)
    omega_addr = np.asarray([int(ss.GENCLS.omega.a[p]) for p in vsg_pos], dtype=int)
    f_omega = np.asarray([f_res[a] for a in omega_addr], dtype=float)
    gy_cond = float(np.linalg.cond(gy))
    return {
        "vsg_pos": vsg_pos,
        "omega": omega,
        "m_base": m_base,
        "d_base": d_base,
        "f_omega": f_omega,
        "fy": fy,
        "gy": gy,
        "gy_cond": gy_cond,
        "max_abs_f": float(np.max(np.abs(f_res))),
        "max_abs_g": float(np.max(np.abs(g_res))),
        "state_dim": int(fy.shape[0]),
        "algebraic_dim": int(gy.shape[0]),
    }


def _make_residual_callback(env, snap):
    """Callback u (8-vector [dM1..dM4, dD1..dD4]) -> (f, g) at frozen x*, y*."""
    ss = env.ss
    models = ss.exist.pflow_tds
    vsg_idx = list(env.vsg_idx)
    vsg_pos = snap["vsg_pos"]
    m_base = snap["m_base"]
    d_base = snap["d_base"]

    def callback(u: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        u = np.asarray(u, dtype=float)
        if u.shape != (8,):
            raise ValueError(f"input must be shape (8,), got {u.shape}")
        # write M/D = base + perturbation (M write also mutates dae.Tf; f/g do
        # not depend on Tf, and the next callback rewrites all 8 values, so no
        # explicit Tf restore is needed between calls).
        for i, pos in enumerate(vsg_pos):
            ss.GENCLS.set("M", vsg_idx[i], float(m_base[i] + u[i]), attr="v")
            ss.GENCLS.set("D", vsg_idx[i], float(d_base[i] + u[4 + i]), attr="v")
        ss.TDS.fg_update(models=models)
        f = np.asarray(ss.dae.f, dtype=float).copy()
        g = np.asarray(ss.dae.g, dtype=float).copy()
        # restore base so the env stays at the equilibrium for any later use
        for i, pos in enumerate(vsg_pos):
            ss.GENCLS.set("M", vsg_idx[i], float(m_base[i]), attr="v")
            ss.GENCLS.set("D", vsg_idx[i], float(d_base[i]), attr="v")
        return f, g

    return callback


def _fold_once(env, snap, callback, h):
    from andes_rl_kundur.env.andes.model_first_contract import (
        finite_difference_input_jacobians,
    )
    from andes_rl_kundur.evaluation.r405_linearization import fold_input_columns

    centre = np.concatenate([snap["m_base"], snap["d_base"]])
    jac = finite_difference_input_jacobians(
        callback, equilibrium_input=centre, step=float(h)
    )
    b = fold_input_columns(jac.f_input, jac.g_input, snap["fy"], snap["gy"])
    col_names = [f"dM_{i+1}" for i in range(4)] + [f"dD_{i+1}" for i in range(4)]
    return {
        "h": float(h),
        "columns": {
            name: {
                "max_abs": float(np.max(np.abs(b[:, j]))),
                "norm2": float(np.linalg.norm(b[:, j])),
            }
            for j, name in enumerate(col_names)
        },
        "midpoint_ratios": [float(v) for v in jac.midpoint_ratios],
    }


def _verdict(folds: list[dict], snap: dict) -> dict:
    col_names = [f"dM_{i+1}" for i in range(4)] + [f"dD_{i+1}" for i in range(4)]
    # equilibrium gates
    max_omega_dev = float(np.max(np.abs(np.asarray(snap["omega"], float) - 1.0)))
    max_f_omega = float(np.max(np.abs(snap["f_omega"])))
    eq_ok = max_omega_dev <= EQ_GATE and max_f_omega <= EQ_GATE
    gy_ok = snap["gy_cond"] < GY_COND_LIMIT

    # per-column: max over h grid; h-convergence = max |B_h1 - B_h2| across grid
    per_col = {}
    for name in col_names:
        vals = [f["columns"][name]["max_abs"] for f in folds]
        max_abs = max(vals)
        convergence = max(abs(a - b) for a, b in zip(vals, vals[1:])) if len(vals) > 1 else 0.0
        per_col[name] = {"max_abs": max_abs, "h_convergence": convergence}

    all_zero = all(c["max_abs"] <= MATERIALITY and c["h_convergence"] <= MATERIALITY
                   for c in per_col.values())
    any_nonzero = any(c["max_abs"] > MATERIALITY and c["h_convergence"] <= MATERIALITY
                      for c in per_col.values())

    if not (eq_ok and gy_ok):
        verdict = "CANARY-INVALID"
    elif all_zero:
        verdict = "ZERO-FIRST-ORDER-AUTHORITY"
    elif any_nonzero:
        verdict = "NONZERO-FIRST-ORDER-AUTHORITY"
    else:
        verdict = "CANARY-INVALID"  # max_abs > materiality but not h-convergent
    return {
        "verdict": verdict,
        "equilibrium_ok": bool(eq_ok),
        "gy_ok": bool(gy_ok),
        "max_omega_dev": max_omega_dev,
        "max_f_omega": max_f_omega,
        "gy_cond": snap["gy_cond"],
        "materiality": MATERIALITY,
        "per_column": per_col,
    }


def _write_json(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    (path.parent / (path.name + ".sha256")).write_text(
        f"{digest}  {path.name}\n", encoding="utf-8"
    )
    return digest


def rehearse() -> int:
    env = _build_env()
    try:
        env.reset(delta_u={})
        snap = _snapshot(env)
        cb = _make_residual_callback(env, snap)
        # one column, one h: perturb dM_1 at h=1e-3
        centre = np.concatenate([snap["m_base"], snap["d_base"]])
        p = centre.copy(); p[0] += 1e-3
        n = centre.copy(); n[0] -= 1e-3
        fp, gp = cb(p)
        fn, gn = cb(n)
        checks = {
            "f_shape_stable": fp.shape[0] == snap["fy"].shape[0] and fn.shape[0] == snap["fy"].shape[0],
            "g_shape_stable": gp.shape[0] == snap["gy"].shape[0] and gn.shape[0] == snap["gy"].shape[0],
            "f_finite": bool(np.all(np.isfinite(fp)) and np.all(np.isfinite(fn))),
            "g_finite": bool(np.all(np.isfinite(gp)) and np.all(np.isfinite(gn))),
            "gy_invertible": bool(np.linalg.cond(snap["gy"]) < GY_COND_LIMIT),
            "equilibrium_omega": float(np.max(np.abs(np.asarray(snap["omega"], float) - 1.0))),
            "equilibrium_f_omega": float(np.max(np.abs(snap["f_omega"]))),
        }
        print(json.dumps({"rehearse_ok": True, "checks": checks}, indent=2))
        return 0
    finally:
        env.close()


def analyse() -> int:
    env = _build_env()
    try:
        env.reset(delta_u={})
        snap = _snapshot(env)
        cb = _make_residual_callback(env, snap)
        folds = [_fold_once(env, snap, cb, h) for h in H_GRID]
        verdict = _verdict(folds, snap)
        payload = {
            "schema_version": 1,
            "round": "R446",
            "object": "Object A direct M/D (four VSG GENCLS)",
            "measurement": "B_{u,r} = f_u - f_y g_y^-1 g_u finite difference",
            "snapshot": {
                "omega": [float(v) for v in snap["omega"]],
                "m_base": [float(v) for v in snap["m_base"]],
                "d_base": [float(v) for v in snap["d_base"]],
                "gy_cond": snap["gy_cond"],
                "max_abs_f": snap["max_abs_f"],
                "max_abs_g": snap["max_abs_g"],
                "state_dim": snap["state_dim"],
                "algebraic_dim": snap["algebraic_dim"],
            },
            "h_grid": [f["h"] for f in folds],
            "folds": folds,
            **verdict,
        }
        digest = _write_json(OUT / "formal_analysis.json", payload)
        print(f"verdict={verdict['verdict']} sha256={digest}")
        print(f"per_column_max_abs=" + json.dumps(
            {k: f"{v['max_abs']:.3e}" for k, v in verdict["per_column"].items()}
        ))
        return 0
    finally:
        env.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["rehearse", "analyse"],
                        help="rehearse = 1 column/1 h; analyse = full measurement")
    args = parser.parse_args(argv)
    try:
        return rehearse() if args.mode == "rehearse" else analyse()
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
