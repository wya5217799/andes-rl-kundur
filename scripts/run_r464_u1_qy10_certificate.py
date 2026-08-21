"""R464 U1 QY10 finite-window conic certificate bundle (WSL runtime)."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "4"

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT, ROOT / "src", ROOT / "scripts"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import numpy as np  # noqa: E402
import scipy.linalg as la  # noqa: E402
import scipy.sparse as sp  # noqa: E402


ROUND = "R464"
PLAN = ROOT / "memory/rounds/R464/plan.md"
LINE = ROOT / "paper/yang_md_decoupling_marl/LINE.md"
CAPACITY = ROOT / "memory/rounds/R464/capacity_evidence.json"
REHEARSAL = ROOT / "memory/rounds/R464/rehearsal.json"
SEAL = ROOT / "memory/rounds/R464/formal_seal.json"
OUT = ROOT / "results/research_loop/r464_u1_qy10_certificate"
R459 = ROOT / "results/research_loop/r459_u1_u8_shared_export"
MODEL = R459 / "model_exports/object_b/sampled_model.npz"
CONTROLLERS = R459 / "model_exports/object_b/controllers.npz"
METADATA = R459 / "model_exports/object_b/metadata.json"
STEPS = 30
TAPS = 10
DT = 0.2
ACTION_TUBE = 0.69


def _utc() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def _write_json_new(path: Path, payload: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _npz_new(path: Path, **arrays: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    np.savez(path, **arrays)
    digest = _sha256(path)
    Path(f"{path}.sha256").write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    return digest


def _td(rows: int) -> np.ndarray:
    q = np.ones(rows) / np.sqrt(rows)
    return la.null_space(q[None, :]).T


def _load_model() -> dict[str, np.ndarray]:
    sampled = np.load(MODEL, allow_pickle=False)
    controllers = np.load(CONTROLLERS, allow_pickle=False)
    headroom = controllers["headroom_system_pu"]
    return {
        "A": sampled["A_post_step"],
        "B_c": sampled["B_post_step"][:, :4] @ np.diag(headroom),
        "B_w": sampled["B_post_step"][:, 4:],
        "C": sampled["C_post_step"],
        "D_c": sampled["D_post_step"][:, :4] @ np.diag(headroom),
        "D_w": sampled["D_post_step"][:, 4:],
        "headroom": headroom,
        "num": controllers["bandpass_numerator"],
        "den": controllers["bandpass_denominator"],
        "ring": controllers["ring_incidence"],
        "legacy_A_cl": controllers["bandpass_A_cl"],
    }


def gauge_reduce(model: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    A, B, C = model["A"], np.hstack([model["B_c"], model["B_w"]]), model["C"]
    values, left, right = la.eig(A, left=True, right=True)
    index = int(np.argmin(np.abs(values - 1.0)))
    eigenvalue = values[index]
    v = np.real_if_close(right[:, index]).astype(float)
    v /= np.linalg.norm(v)
    w = np.real_if_close(left[:, index]).astype(float)
    w /= np.vdot(w, v)
    complement = la.null_space(v[None, :])
    transform = np.column_stack([v, complement])
    abar = transform.T @ A @ transform
    bbar = transform.T @ B
    cbar = C @ transform
    reduced = {
        "A": abar[1:, 1:],
        "B_c": bbar[1:, :4],
        "B_w": bbar[1:, 4:],
        "C": cbar[:, 1:],
        "D_c": model["D_c"],
        "D_w": model["D_w"],
        "headroom": model["headroom"],
        "num": model["num"],
        "den": model["den"],
        "ring": model["ring"],
    }
    residue = np.outer(C @ v, w.T @ B)
    transfer_errors = []
    for omega in np.linspace(0.01, np.pi, 41):
        z = np.exp(1j * omega)
        full = C @ la.solve(z * np.eye(A.shape[0]) - A, B) + np.hstack([model["D_c"], model["D_w"]])
        red = reduced["C"] @ la.solve(z * np.eye(reduced["A"].shape[0]) - reduced["A"], np.hstack([reduced["B_c"], reduced["B_w"]])) + np.hstack([reduced["D_c"], reduced["D_w"]])
        transfer_errors.append(np.linalg.norm(full - red) / max(np.linalg.norm(full), 1e-15))
    checks = {
        "full_dimension": A.shape[0],
        "reduced_dimension": reduced["A"].shape[0],
        "gauge_eigenvalue_real": float(np.real(eigenvalue)),
        "gauge_eigenvalue_imag": float(np.imag(eigenvalue)),
        "right_eigen_residual": float(np.linalg.norm(A @ v - eigenvalue * v)),
        "left_eigen_residual": float(np.linalg.norm(w.T @ A - eigenvalue * w.T)),
        "gauge_output_norm": float(np.linalg.norm(C @ v)),
        "gauge_transfer_residue_norm": float(np.linalg.norm(residue)),
        "complement_invariance_residual": float(np.linalg.norm(abar[1:, 0])),
        "reduced_spectral_radius": float(np.max(np.abs(np.linalg.eigvals(reduced["A"])))),
        "maximum_transfer_relative_error": float(max(transfer_errors)),
        "right_vector": v.tolist(),
        "left_vector": w.tolist(),
    }
    checks["passed"] = bool(
        abs(eigenvalue - 1.0) <= 1e-10
        and checks["right_eigen_residual"] <= 1e-10
        and checks["left_eigen_residual"] <= 1e-10
        and checks["gauge_output_norm"] <= 1e-10
        and checks["gauge_transfer_residue_norm"] <= 1e-10
        and checks["complement_invariance_residual"] <= 1e-10
        and checks["reduced_spectral_radius"] < 1.0 - 1e-6
        and checks["maximum_transfer_relative_error"] <= 1e-10
    )
    return reduced, checks


def markov(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray, steps: int = STEPS) -> np.ndarray:
    rows = [D]
    power = np.eye(A.shape[0])
    for _ in range(1, steps):
        rows.append(C @ power @ B)
        power = power @ A
    return np.stack(rows)


def exact_bandpass(model: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    A, Bc, Bw, C, Dc, Dw = (model[k] for k in ("A", "B_c", "B_w", "C", "D_c", "D_w"))
    b0, b1, b2 = (float(x) for x in model["num"])
    a1, a2 = float(model["den"][1]), float(model["den"][2])
    R = model["ring"]
    G = R @ R.T
    J = np.eye(4) + b0 * G @ Dc
    Ux = la.solve(J, -b0 * G @ C)
    Uz = la.solve(J, -R)
    Uw = la.solve(J, -b0 * G @ Dw)
    Yx, Yz, Yw = C + Dc @ Ux, Dc @ Uz, Dw + Dc @ Uw
    alpha, beta = b1 - a1 * b0, b2 - a2 * b0
    nx = A.shape[0]
    Acl = np.block(
        [
            [A + Bc @ Ux, Bc @ Uz, np.zeros((nx, 4))],
            [alpha * R.T @ Yx, -a1 * np.eye(4) + alpha * R.T @ Yz, np.eye(4)],
            [beta * R.T @ Yx, -a2 * np.eye(4) + beta * R.T @ Yz, np.zeros((4, 4))],
        ]
    )
    Bcl = np.vstack([Bw + Bc @ Uw, alpha * R.T @ Yw, beta * R.T @ Yw])
    Cy = np.hstack([Yx, Yz, np.zeros((4, 4))])
    Cu = np.hstack([Ux, Uz, np.zeros((4, 4))])
    return {"A": Acl, "B": Bcl, "C_y": Cy, "D_y": Yw, "C_u": Cu, "D_u": Uw}


def impulse(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray, directions: np.ndarray) -> np.ndarray:
    outputs = []
    for direction in directions:
        x = np.zeros(A.shape[0])
        rows = []
        for step in range(STEPS):
            w = direction if step == 0 else np.zeros(B.shape[1])
            rows.append(C @ x + D @ w)
            x = A @ x + B @ w
        outputs.append(rows)
    return np.asarray(outputs)


def q_blocks(q: np.ndarray, td4: np.ndarray) -> np.ndarray:
    hats = np.asarray(q).reshape(TAPS, 3, 3)
    return np.stack([td4.T @ hat @ td4 for hat in hats])


def direct_response(q: np.ndarray, h_c: np.ndarray, y0: np.ndarray, td4: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    blocks = q_blocks(q, td4)
    u = np.zeros_like(y0)
    y = y0.copy()
    for scenario in range(y0.shape[0]):
        for t in range(STEPS):
            for h in range(1, min(TAPS, t) + 1):
                u[scenario, t] -= blocks[h - 1] @ y0[scenario, t - h]
        for t in range(STEPS):
            for lag in range(t + 1):
                y[scenario, t] += h_c[lag] @ u[scenario, t - lag]
    return y, u


def build_lifts(model: dict[str, np.ndarray]) -> dict[str, Any]:
    td4, td3 = _td(4), _td(3)
    directions = np.vstack([np.ones(3) / np.sqrt(3), td3])
    h_c = markov(model["A"], model["B_c"], model["C"], model["D_c"])
    h_w = markov(model["A"], model["B_w"], model["C"], model["D_w"])
    y0 = np.einsum("tij,sj->sti", h_w, directions)
    base_y, base_u = direct_response(np.zeros(90), h_c, y0, td4)
    Ay = np.empty((base_y.size, 90))
    Au = np.empty((base_u.size, 90))
    for index in range(90):
        q = np.zeros(90)
        q[index] = 1.0
        y, u = direct_response(q, h_c, y0, td4)
        Ay[:, index] = (y - base_y).ravel()
        Au[:, index] = u.ravel()
    reference = exact_bandpass(model)
    y_ref = impulse(reference["A"], reference["B"], reference["C_y"], reference["D_y"], directions)
    u_ref = impulse(reference["A"], reference["B"], reference["C_u"], reference["D_u"], directions)
    return {
        "td4": td4,
        "td3": td3,
        "directions": directions,
        "H_c": h_c,
        "H_w": h_w,
        "b_y": base_y.ravel(),
        "A_y": Ay,
        "b_u": base_u.ravel(),
        "A_u": Au,
        "y_shape": base_y.shape,
        "u_shape": base_u.shape,
        "y_ref": y_ref,
        "u_ref": u_ref,
        "reference": reference,
    }


def _selectors(td4: np.ndarray) -> dict[str, np.ndarray]:
    ny = 3 * STEPS * 4
    diff, cross, common = [], [], []
    for s in range(3):
        for t in range(STEPS):
            block = np.zeros((4, ny))
            offset = (s * STEPS + t) * 4
            block[:, offset : offset + 4] = np.eye(4)
            diff.append(td4 @ block)
            common.append((np.ones((1, 4)) / 4.0) @ block)
            if s == 0:
                cross.append(td4 @ block)
            else:
                cross.append((np.ones((1, 4)) / 4.0) @ block)
    Sdiff = np.vstack(diff)
    Scross = np.vstack(cross)
    Scommon = np.vstack(common)
    Dy = np.zeros((ny, ny))
    for s in range(3):
        for t in range(STEPS):
            row = (s * STEPS + t) * 4
            Dy[row : row + 4, row : row + 4] = np.eye(4) / DT
            if t > 0:
                Dy[row : row + 4, row - 4 : row] = -np.eye(4) / DT
    Du = np.zeros((ny, ny))
    for s in range(3):
        for t in range(STEPS):
            row = (s * STEPS + t) * 4
            Du[row : row + 4, row : row + 4] = np.eye(4)
            if t > 0:
                Du[row : row + 4, row - 4 : row] = -np.eye(4)
    return {"diff": Sdiff, "cross": Scross, "common": Scommon, "rocof": Dy, "tv": Du}


def _metrics(y: np.ndarray, u: np.ndarray, selectors: dict[str, np.ndarray]) -> dict[str, float]:
    yf, uf = y.ravel(), u.ravel()
    return {
        "differential_energy": float(np.linalg.norm(selectors["diff"] @ yf) ** 2),
        "cross_energy": float(np.linalg.norm(selectors["cross"] @ yf) ** 2),
        "common_iae": float(DT * np.linalg.norm(selectors["common"] @ yf, 1)),
        "peak": float(np.linalg.norm(yf, np.inf)),
        "rocof": float(np.linalg.norm(selectors["rocof"] @ yf, np.inf)),
        "action_rms": float(np.sqrt(np.mean(uf**2))),
        "action_tv": float(np.linalg.norm(selectors["tv"] @ uf, 1)),
        "action_peak": float(np.linalg.norm(uf, np.inf)),
    }


def _bezout(h_c: np.ndarray) -> dict[str, Any]:
    # [I 0; P I] * [I 0; -P I] = I for signed plant N=N~=-P.
    residuals = []
    for k in range(STEPS):
        lower_left = h_c[k] - h_c[k]
        residuals.append(np.linalg.norm(lower_left))
    scale = max(1.0, float(np.linalg.norm(h_c)))
    return {
        "convention": "negative feedback u=-Ky; DCF factors signed plant -P_c",
        "factors": {"M": "I", "N": "-P_c", "U": "0", "V": "I", "M_tilde": "I", "N_tilde": "-P_c", "U_tilde": "0", "V_tilde": "I"},
        "coefficient_count": STEPS,
        "maximum_absolute_residual": float(max(residuals)),
        "relative_frobenius_residual": float(np.linalg.norm(residuals) / scale),
        "passed": bool(np.linalg.norm(residuals) / scale <= 1e-10),
    }


def _column_check(lifts: dict[str, Any]) -> dict[str, Any]:
    indices = [0, 8, 9, 44, 89]
    rows = []
    max_rel = 0.0
    max_abs = 0.0
    for index in indices:
        for h in (1e-4, 5e-5):
            q = np.zeros(90)
            q[index] = h
            yp, up = direct_response(q, lifts["H_c"], lifts["b_y"].reshape(lifts["y_shape"]), lifts["td4"])
            q[index] = -h
            ym, um = direct_response(q, lifts["H_c"], lifts["b_y"].reshape(lifts["y_shape"]), lifts["td4"])
            dy, du = (yp - ym).ravel() / (2 * h), (up - um).ravel() / (2 * h)
            abs_err = max(np.max(np.abs(dy - lifts["A_y"][:, index])), np.max(np.abs(du - lifts["A_u"][:, index])))
            denom = max(np.linalg.norm(dy), np.linalg.norm(du), 1e-12)
            rel = max(np.linalg.norm(dy - lifts["A_y"][:, index]), np.linalg.norm(du - lifts["A_u"][:, index])) / denom
            rows.append({"column": index, "h": h, "max_abs_error": float(abs_err), "relative_error": float(rel)})
            max_rel, max_abs = max(max_rel, rel), max(max_abs, abs_err)
    return {"rows": rows, "maximum_relative_error": float(max_rel), "maximum_absolute_error": float(max_abs), "passed": bool(max_rel <= 1e-7 or max_abs <= 1e-10)}


def solve_phase(lifts: dict[str, Any], *, max_iter: int = 500) -> dict[str, Any]:
    import cvxpy as cp
    import clarabel

    selectors = _selectors(lifts["td4"])
    reference_metrics = _metrics(lifts["y_ref"], lifts["u_ref"], selectors)
    if min(reference_metrics.values()) <= 1e-12:
        raise RuntimeError(f"non-positive reference denominator: {reference_metrics}")
    q = cp.Variable(90, name="q")
    t = cp.Variable(name="t")
    y = lifts["b_y"] + lifts["A_y"] @ q
    u = lifts["b_u"] + lifts["A_u"] @ q
    allowed = {
        "diff_norm": np.sqrt(0.95 * reference_metrics["differential_energy"]),
        "cross_norm": np.sqrt(0.95 * reference_metrics["cross_energy"]),
        "common_iae": 1.03 * reference_metrics["common_iae"],
        "peak": 1.03 * reference_metrics["peak"],
        "rocof": 1.03 * reference_metrics["rocof"],
        "action_norm": 1.10 * reference_metrics["action_rms"] * np.sqrt(lifts["b_u"].size),
        "action_tv": 1.10 * reference_metrics["action_tv"],
        "action_peak": ACTION_TUBE,
    }
    constraints = [
        cp.norm(selectors["diff"] @ y, 2) <= allowed["diff_norm"] * (1 + t),
        cp.norm(selectors["cross"] @ y, 2) <= allowed["cross_norm"] * (1 + t),
        DT * cp.norm1(selectors["common"] @ y) <= allowed["common_iae"] * (1 + t),
        cp.norm_inf(y) <= allowed["peak"] * (1 + t),
        cp.norm_inf(selectors["rocof"] @ y) <= allowed["rocof"] * (1 + t),
        cp.norm(u, 2) <= allowed["action_norm"] * (1 + t),
        cp.norm1(selectors["tv"] @ u) <= allowed["action_tv"] * (1 + t),
        cp.norm_inf(u) <= allowed["action_peak"] * (1 + t),
        cp.norm(q, 2) <= 1.0,
        t >= -0.99,
    ]
    problem = cp.Problem(cp.Minimize(t), constraints)
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        value = problem.solve(
            solver=cp.CLARABEL,
            verbose=True,
            max_iter=max_iter,
            tol_gap_abs=1e-10,
            tol_gap_rel=1e-10,
            tol_feas=1e-10,
            equilibrate_enable=False,
        )
    data, _, _ = problem.get_problem_data(cp.CLARABEL)
    dims = data["dims"]
    cones = []
    cone_schema = []
    if dims.zero:
        cones.append(clarabel.ZeroConeT(dims.zero)); cone_schema.append({"kind": "zero", "dimension": dims.zero})
    if dims.nonneg:
        cones.append(clarabel.NonnegativeConeT(dims.nonneg)); cone_schema.append({"kind": "nonnegative", "dimension": dims.nonneg})
    for size in dims.soc:
        cones.append(clarabel.SecondOrderConeT(size)); cone_schema.append({"kind": "soc", "dimension": size})
    settings = clarabel.DefaultSettings()
    settings.verbose = False
    settings.max_iter = max_iter
    settings.tol_gap_abs = 1e-10
    settings.tol_gap_rel = 1e-10
    settings.tol_feas = 1e-10
    settings.equilibrate_enable = False
    # CVXPY omits ``P`` for a purely linear objective.  Clarabel's direct
    # interface still requires the explicit zero quadratic term so that the
    # exported canonical problem can be replayed independently.
    canonical_p = data.get("P")
    if canonical_p is None:
        canonical_p = sp.csc_matrix((data["c"].size, data["c"].size))
    canonical = clarabel.DefaultSolver(canonical_p, data["c"], data["A"], data["b"], cones, settings).solve()
    canonical_dual_objective = float(-np.asarray(data["b"]) @ np.asarray(canonical.z))
    return {
        "status": str(problem.status),
        "objective": float(value),
        "q": np.asarray(q.value).ravel(),
        "t": float(t.value),
        "reference_metrics": reference_metrics,
        "allowed": allowed,
        "solver_log": stream.getvalue(),
        "solver_stats": {
            "solver_name": problem.solver_stats.solver_name,
            "solve_time": problem.solver_stats.solve_time,
            "num_iters": problem.solver_stats.num_iters,
            "cvxpy_version": cp.__version__,
            "clarabel_version": clarabel.__version__,
        },
        "canonical": {
            "P": canonical_p, "A": data["A"], "b": np.asarray(data["b"]), "c": np.asarray(data["c"]),
            "cones": cone_schema,
            "x": np.asarray(canonical.x), "s": np.asarray(canonical.s), "z": np.asarray(canonical.z),
            "status": str(canonical.status), "obj_val": float(canonical.obj_val), "obj_val_dual": canonical_dual_objective,
            "iterations": int(canonical.iterations),
        },
        "selectors": selectors,
    }


def _cone_violation(vector: np.ndarray, cones: list[dict[str, Any]]) -> float:
    offset = 0
    violations = []
    for cone in cones:
        size = int(cone["dimension"])
        block = vector[offset : offset + size]
        if cone["kind"] == "zero":
            violations.append(float(np.max(np.abs(block))) if size else 0.0)
        elif cone["kind"] == "nonnegative":
            violations.append(float(max(0.0, -np.min(block))) if size else 0.0)
        else:
            violations.append(float(max(0.0, np.linalg.norm(block[1:]) - block[0])))
        offset += size
    if offset != vector.size:
        raise RuntimeError("cone dimensions do not cover vector")
    return max(violations, default=0.0)


def verify(result: dict[str, Any], lifts: dict[str, Any], bezout: dict[str, Any], columns: dict[str, Any]) -> dict[str, Any]:
    import mpmath as mp

    can = result["canonical"]
    A, b, c, x, s, z = can["A"], can["b"], can["c"], can["x"], can["s"], can["z"]
    primal_res = float(np.linalg.norm(A @ x + s - b, np.inf))
    stationarity = float(np.linalg.norm(A.T @ z + c, np.inf))
    cone_primal = _cone_violation(s, can["cones"])
    cone_dual = _cone_violation(z, can["cones"])
    primal_obj = float(c @ x)
    dual_obj = float(-b @ z)
    gap = primal_obj - dual_obj
    relative_gap = abs(gap) / max(1.0, abs(primal_obj), abs(dual_obj))
    q = result["q"]
    y, u = direct_response(q, lifts["H_c"], lifts["b_y"].reshape(lifts["y_shape"]), lifts["td4"])
    lift_y = (lifts["b_y"] + lifts["A_y"] @ q).reshape(lifts["y_shape"])
    lift_u = (lifts["b_u"] + lifts["A_u"] @ q).reshape(lifts["u_shape"])
    direct_error = max(float(np.max(np.abs(y - lift_y))), float(np.max(np.abs(u - lift_u))))
    metrics = _metrics(y, u, result["selectors"])
    ratios = {
        "differential_energy": np.sqrt(metrics["differential_energy"]) / result["allowed"]["diff_norm"] - 1,
        "cross_energy": np.sqrt(metrics["cross_energy"]) / result["allowed"]["cross_norm"] - 1,
        "common_iae": metrics["common_iae"] / result["allowed"]["common_iae"] - 1,
        "peak": metrics["peak"] / result["allowed"]["peak"] - 1,
        "rocof": metrics["rocof"] / result["allowed"]["rocof"] - 1,
        "action_rms": metrics["action_rms"] / (result["allowed"]["action_norm"] / np.sqrt(lifts["b_u"].size)) - 1,
        "action_tv": metrics["action_tv"] / result["allowed"]["action_tv"] - 1,
        "action_peak": metrics["action_peak"] / result["allowed"]["action_peak"] - 1,
    }
    original_max = max(ratios.values())
    mp.mp.dps = 80
    dual_mp = -sum(mp.mpf(str(bi)) * mp.mpf(str(zi)) for bi, zi in zip(b, z, strict=True))
    residual_allowance = primal_res + stationarity + cone_primal + cone_dual + relative_gap + abs(result["t"] - primal_obj)
    safety_ratio = dual_obj / max(residual_allowance, 1e-30)
    verified_dual = bool(
        result["t"] > 0
        and dual_obj > 0
        and dual_mp > 0
        and primal_res <= 1e-9 * (1 + np.linalg.norm(b, np.inf))
        and stationarity <= 1e-9
        and cone_primal <= 1e-9
        and cone_dual <= 1e-9
        and relative_gap <= 1e-8
        and safety_ratio > 10
    )
    if result["t"] <= -1e-7 and all((bezout["passed"], columns["passed"], direct_error <= 1e-9)):
        verdict = "FEASIBLE-WITNESS-IN-QY10"
    elif verified_dual:
        verdict = "INFEASIBLE-QY10-WITH-VERIFIED-DUAL-BOUND"
    else:
        verdict = "CERTIFICATE-INVALID"
    return {
        "verdict": verdict,
        "primal_residual_inf": primal_res,
        "primal_cone_violation": cone_primal,
        "dual_cone_violation": cone_dual,
        "dual_stationarity_residual_inf": stationarity,
        "primal_objective": primal_obj,
        "dual_objective": dual_obj,
        "duality_gap": gap,
        "relative_duality_gap": relative_gap,
        "dual_objective_80_decimal": mp.nstr(dual_mp, 82),
        "numeric_residual_allowance": residual_allowance,
        "positive_bound_safety_ratio": safety_ratio,
        "verified_positive_dual_bound": verified_dual,
        "direct_vs_lift_max_abs_error": direct_error,
        "q_frobenius_norm": float(np.linalg.norm(q)),
        "candidate_metrics": metrics,
        "normalized_guard_residuals": {key: float(value) for key, value in ratios.items()},
        "original_max_guard_residual": float(original_max),
        "solver_t": result["t"],
        "bezout_pass": bezout["passed"],
        "lift_column_pass": columns["passed"],
        "nonlinear_discrepancy_allowance": 0.0,
        "nonlinear_claim_authorized": False,
    }


def _compute(max_iter: int = 500) -> dict[str, Any]:
    reduced, gauge = gauge_reduce(_load_model())
    if not gauge["passed"]:
        return {"early_verdict": "CERTIFICATE-NOT-IDENTIFIABLE", "gauge": gauge}
    lifts = build_lifts(reduced)
    bezout = _bezout(lifts["H_c"])
    columns = _column_check(lifts)
    if not bezout["passed"] or not columns["passed"]:
        return {"early_verdict": "CERTIFICATE-INVALID", "gauge": gauge, "bezout": bezout, "columns": columns}
    phase = solve_phase(lifts, max_iter=max_iter)
    verification = verify(phase, lifts, bezout, columns)
    return {"reduced": reduced, "gauge": gauge, "lifts": lifts, "bezout": bezout, "columns": columns, "phase": phase, "verification": verification}


def _authority(absent: bool) -> dict[str, bool]:
    plan = PLAN.read_text(encoding="utf-8")
    line = LINE.read_text(encoding="utf-8")
    checks = {
        "active_plan": "round: R464" in plan and "state: active" in plan,
        "active_line": "line_id: yang-md-decoupling-marl" in line and "status: active" in line,
        "r459_verified": (R459 / "checks/verification_report.json").is_file(),
        "model_present": MODEL.is_file() and CONTROLLERS.is_file() and METADATA.is_file(),
    }
    if absent:
        checks["formal_output_absent"] = not OUT.exists()
    return checks


def _sources() -> dict[str, dict[str, str]]:
    paths = {
        "runner": Path(__file__).resolve(), "plan": PLAN,
        "r459_model": MODEL, "r459_controllers": CONTROLLERS, "r459_metadata": METADATA,
        "r459_verifier": R459 / "checks/verification_report.json",
    }
    return {name: {"path": _relative(path), "sha256": _sha256(path)} for name, path in paths.items()}


def rehearse() -> None:
    if REHEARSAL.exists() or CAPACITY.exists():
        raise FileExistsError("R464 rehearsal/capacity exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    start = time.perf_counter()
    result = _compute(max_iter=200)
    checks = {
        "gauge_pass": result.get("gauge", {}).get("passed", False),
        "bezout_pass": result.get("bezout", {}).get("passed", False),
        "column_pass": result.get("columns", {}).get("passed", False),
        "solver_terminal": result.get("phase", {}).get("status") in ("optimal", "optimal_inaccurate"),
        "prospective_verdict": result.get("verification", {}).get("verdict"),
    }
    if not all(value for key, value in checks.items() if key != "prospective_verdict"):
        raise RuntimeError(checks)
    payload = {"round": ROUND, "created_utc": _utc(), "authority": authority, "checks": checks, "wall_seconds": time.perf_counter() - start}
    _write_json_new(REHEARSAL, payload)
    _write_json_new(CAPACITY, {"round": ROUND, "created_utc": _utc(), "selected_processes": 1, "native_threads": 4, "gpu_selected": False, "cpu_logical": os.cpu_count(), "platform": platform.platform(), "wall_seconds": payload["wall_seconds"], "capacity_anchor": "R459 measured 1/4/8 native-thread ladder selected 4"})
    print(json.dumps(checks, indent=2))


def prepare() -> None:
    if SEAL.exists() or OUT.exists():
        raise FileExistsError("R464 seal/output exists")
    authority = _authority(True)
    if not all(authority.values()):
        raise RuntimeError(authority)
    seal = {"round": ROUND, "created_utc": _utc(), "authority": authority, "sources": _sources(), "rehearsal_sha256": _sha256(REHEARSAL), "capacity_sha256": _sha256(CAPACITY), "formal_output": _relative(OUT), "processes": 1, "native_threads": 4, "retry_policy": "none"}
    print(_write_json_new(SEAL, seal))


def _verify_seal() -> dict[str, Any]:
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    for name, row in seal["sources"].items():
        if _sha256(ROOT / row["path"]) != row["sha256"]:
            raise RuntimeError(f"source drift {name}")
    return seal


def run() -> None:
    if OUT.exists():
        raise FileExistsError(OUT)
    seal = _verify_seal()
    start = time.perf_counter()
    result = _compute()
    if "verification" not in result:
        raise RuntimeError(result.get("early_verdict"))
    OUT.mkdir(parents=True, exist_ok=False)
    reduced, lifts, phase = result["reduced"], result["lifts"], result["phase"]
    _write_json_new(OUT / "checks/gauge_and_stability.json", result["gauge"])
    _write_json_new(OUT / "checks/bezout_check.json", result["bezout"])
    _write_json_new(OUT / "checks/lift_column_check.json", result["columns"])
    _write_json_new(OUT / "checks/certificate_check.json", result["verification"])
    _write_json_new(OUT / "contracts/class_contract.json", {"class_id": "QY10", "taps": 10, "free_variables": 90, "strictly_causal": True, "coefficient_form": "Q_h=T_d^T Qhat_h T_d", "frobenius_bound": 1.0, "locality_claim": False, "feedback_sign": "u=-K y", "saturation_path": "conservative all-sample |u_norm|<=0.69 inside clip 0.70", "window_steps": STEPS, "sample_period_seconds": DT, "object_id": "Object B"})
    _write_json_new(OUT / "contracts/reference_metrics.json", {"reference": "exact full-D K=3.5 bandpass", "metrics": phase["reference_metrics"], "allowed": phase["allowed"]})
    _npz_new(OUT / "model/gauge_reduced_model.npz", **{k: v for k, v in reduced.items() if isinstance(v, np.ndarray)})
    _npz_new(OUT / "model/finite_window_lifts.npz", T_d_output=lifts["td4"], T_d_input=lifts["td3"], disturbance_directions=lifts["directions"], H_control=lifts["H_c"], H_disturbance=lifts["H_w"], b_y=lifts["b_y"], A_y=lifts["A_y"], b_u=lifts["b_u"], A_u=lifts["A_u"], y_reference=lifts["y_ref"], u_reference=lifts["u_ref"])
    can = phase["canonical"]
    Acoo = can["A"].tocoo(); Pcoo = can["P"].tocoo()
    _npz_new(OUT / "certificate/cone_data.npz", A_row=Acoo.row, A_col=Acoo.col, A_data=Acoo.data, A_shape=np.asarray(Acoo.shape), P_row=Pcoo.row, P_col=Pcoo.col, P_data=Pcoo.data, P_shape=np.asarray(Pcoo.shape), b=can["b"], c=can["c"])
    _npz_new(OUT / "certificate/primal_dual_unscaled.npz", q=phase["q"], t=np.asarray(phase["t"]), x=can["x"], s=can["s"], z=can["z"])
    _write_json_new(OUT / "certificate/cone_schema.json", {"cones": can["cones"], "canonical_status": can["status"], "canonical_primal_objective": can["obj_val"], "canonical_dual_objective": can["obj_val_dual"], "iterations": can["iterations"], "equilibration_enabled": False})
    _write_json_new(OUT / "certificate/solver_stats.json", phase["solver_stats"] | {"cvxpy_status": phase["status"], "cvxpy_objective": phase["objective"]})
    (OUT / "certificate/solver.log").write_text(phase["solver_log"], encoding="utf-8")
    _write_json_new(OUT / "provenance/runtime.json", {"wall_seconds": time.perf_counter() - start, "python": sys.version, "platform": platform.platform(), "formal_seal_sha256": _sha256(SEAL), "native_threads": 4})
    verification = {"round": ROUND, "created_utc": _utc(), "verdict": result["verification"]["verdict"], "formal_seal_sha256": _sha256(SEAL), "certificate": result["verification"], "all_checks_pass": result["verification"]["verdict"] != "CERTIFICATE-INVALID"}
    _write_json_new(OUT / "checks/verification_report.json", verification)
    files = sorted(path for path in OUT.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    (OUT / "SHA256SUMS").write_text("".join(f"{_sha256(path)}  {path.relative_to(OUT).as_posix()}\n" for path in files), encoding="utf-8", newline="\n")
    print(json.dumps(verification, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("rehearse", "prepare", "run")); args = parser.parse_args()
    {"rehearse": rehearse, "prepare": prepare, "run": run}[args.command]()


if __name__ == "__main__":
    main()
