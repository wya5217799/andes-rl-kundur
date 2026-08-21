#!/usr/bin/env python3
"""Bounded-class synthesis template and independent infeasibility checks.

The exact VSG plant and metric matrices were not supplied. This module therefore
operates on a finite affine response map that must be derived from a valid Youla
or SLS parameterization. It deliberately separates:

1. construction of the audited affine controller/trajectory class;
2. conic target-margin optimization; and
3. independent verification of primal candidates and Farkas certificates.

The included numerical examples are synthetic and are not results for the
manuscript plant.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np
from scipy.optimize import linprog

try:  # Optional dependency for the actual SOCP template.
    import cvxpy as cp  # type: ignore
except Exception:  # pragma: no cover - environment-dependent
    cp = None


@dataclass
class AffineScenario:
    """One scenario's affine finite-window maps."""

    name: str
    a_d: np.ndarray
    F_d: np.ndarray
    a_cross: np.ndarray
    F_cross: np.ndarray
    a_u: np.ndarray
    F_u: np.ndarray
    a_slew: np.ndarray
    F_slew: np.ndarray
    denom_d: float
    denom_cross: float

    @classmethod
    def from_dict(cls, d: Dict[str, Any], nq: int) -> "AffineScenario":
        def vec(key: str) -> np.ndarray:
            arr = np.asarray(d[key], dtype=float).reshape(-1)
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"{d.get('name', 'scenario')}.{key} contains nonfinite values")
            return arr

        def mat(key: str, rows: int) -> np.ndarray:
            arr = np.asarray(d[key], dtype=float)
            if rows == 0:
                return np.zeros((0, nq))
            arr = arr.reshape(rows, nq)
            if not np.all(np.isfinite(arr)):
                raise ValueError(f"{d.get('name', 'scenario')}.{key} contains nonfinite values")
            return arr

        a_d = vec("a_d")
        a_cross = vec("a_cross")
        a_u = vec("a_u")
        a_slew = vec("a_slew")
        return cls(
            name=str(d.get("name", "scenario")),
            a_d=a_d,
            F_d=mat("F_d", a_d.size),
            a_cross=a_cross,
            F_cross=mat("F_cross", a_cross.size),
            a_u=a_u,
            F_u=mat("F_u", a_u.size),
            a_slew=a_slew,
            F_slew=mat("F_slew", a_slew.size),
            denom_d=float(d["denom_d"]),
            denom_cross=float(d["denom_cross"]),
        )


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    return repr(value)


def _max_or_zero(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float).reshape(-1)
    return 0.0 if values.size == 0 else float(np.max(values))


def load_spec(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        spec = json.load(f)
    validate_spec(spec)
    return spec


def validate_spec(spec: Dict[str, Any]) -> None:
    """Validate dimensions and the fixed-positive normalization assumptions."""
    nq = int(spec["parameter_dimension"])
    if nq < 1:
        raise ValueError("parameter_dimension must be positive")
    if not spec.get("scenarios"):
        raise ValueError("at least one scenario is required")

    for s in spec["scenarios"]:
        scenario = AffineScenario.from_dict(s, nq)
        if not np.isfinite(scenario.denom_d) or scenario.denom_d <= 0:
            raise ValueError(f"{scenario.name}: denom_d must be fixed, finite, and positive")
        if not np.isfinite(scenario.denom_cross) or scenario.denom_cross <= 0:
            raise ValueError(
                f"{scenario.name}: denom_cross must be fixed, finite, and positive"
            )

    constraints = spec["constraints"]
    for key in ("u_max", "slew_max", "target_r_d", "target_r_cross"):
        value = float(constraints[key])
        if not np.isfinite(value) or value < 0:
            raise ValueError(f"constraints.{key} must be finite and nonnegative")

    equalities = spec.get("equalities", {})
    E = np.asarray(equalities.get("E", []), dtype=float)
    f = np.asarray(equalities.get("f", []), dtype=float).reshape(-1)
    if E.size:
        E.reshape(f.size, nq)
    elif f.size:
        raise ValueError("equalities.f is nonempty but equalities.E is empty")

    inequalities = spec.get("inequalities", {})
    G = np.asarray(inequalities.get("G", []), dtype=float)
    h = np.asarray(inequalities.get("h", []), dtype=float).reshape(-1)
    if G.size:
        G.reshape(h.size, nq)
    elif h.size:
        raise ValueError("inequalities.h is nonempty but inequalities.G is empty")


def verify_margin_candidate(
    spec: Dict[str, Any], q: np.ndarray, t: float, tol: float = 1e-7
) -> Dict[str, Any]:
    """Independently recompute all constraints from a candidate ``(q,t)``.

    This verifies primal feasibility only. It does not prove that ``t`` is globally
    optimal and does not provide an infeasibility certificate.
    """
    validate_spec(spec)
    nq = int(spec["parameter_dimension"])
    q = np.asarray(q, dtype=float).reshape(-1)
    if q.size != nq:
        raise ValueError(f"q has length {q.size}; expected {nq}")
    if not np.all(np.isfinite(q)) or not np.isfinite(t):
        raise ValueError("q and t must be finite")

    constraints = spec["constraints"]
    target_d = float(constraints["target_r_d"])
    target_cross = float(constraints["target_r_cross"])
    u_max = float(constraints["u_max"])
    slew_max = float(constraints["slew_max"])

    violations: Dict[str, float] = {"t_nonnegative": float(max(0.0, -t))}

    equalities = spec.get("equalities", {})
    E = np.asarray(equalities.get("E", []), dtype=float)
    f = np.asarray(equalities.get("f", []), dtype=float).reshape(-1)
    if E.size:
        E = E.reshape(f.size, nq)
        violations["generic_equalities_inf"] = _max_or_zero(np.abs(E @ q - f))
    else:
        violations["generic_equalities_inf"] = 0.0

    inequalities = spec.get("inequalities", {})
    G = np.asarray(inequalities.get("G", []), dtype=float)
    h = np.asarray(inequalities.get("h", []), dtype=float).reshape(-1)
    if G.size:
        G = G.reshape(h.size, nq)
        violations["generic_inequalities_max"] = max(0.0, _max_or_zero(G @ q - h))
    else:
        violations["generic_inequalities_max"] = 0.0

    scenario_metrics: List[Dict[str, Any]] = []
    for raw in spec["scenarios"]:
        s = AffineScenario.from_dict(raw, nq)
        y_d = s.a_d + s.F_d @ q
        y_cross = s.a_cross + s.F_cross @ q
        u = s.a_u + s.F_u @ q
        du = s.a_slew + s.F_slew @ q

        norm_d = float(np.linalg.norm(y_d, 2))
        norm_cross = float(np.linalg.norm(y_cross, 2))
        bound_d = float(t * target_d * s.denom_d)
        bound_cross = float(t * target_cross * s.denom_cross)
        v_d = max(0.0, norm_d - bound_d)
        v_cross = max(0.0, norm_cross - bound_cross)
        v_u = max(0.0, _max_or_zero(np.abs(u) - u_max))
        v_slew = max(0.0, _max_or_zero(np.abs(du) - slew_max))

        violations[f"{s.name}.differential_norm"] = v_d
        violations[f"{s.name}.cross_norm"] = v_cross
        violations[f"{s.name}.action_box"] = v_u
        violations[f"{s.name}.slew_box"] = v_slew
        scenario_metrics.append(
            {
                "name": s.name,
                "norm_d": norm_d,
                "bound_d": bound_d,
                "r_d": norm_d / s.denom_d,
                "norm_cross": norm_cross,
                "bound_cross": bound_cross,
                "r_cross": norm_cross / s.denom_cross,
                "max_abs_action": _max_or_zero(np.abs(u)),
                "max_abs_slew": _max_or_zero(np.abs(du)),
            }
        )

    max_violation = max(violations.values(), default=0.0)
    return {
        "primal_feasible_within_tolerance": bool(max_violation <= tol),
        "tolerance": float(tol),
        "max_constraint_violation": float(max_violation),
        "violations": violations,
        "scenario_metrics": scenario_metrics,
        "warning": "Primal feasibility is not a proof of global optimality or infeasibility.",
    }


def solve_margin_socp(spec: Dict[str, Any], solver: str | None = None) -> Dict[str, Any]:
    """Solve the finite-dimensional target-scaling SOCP.

    A rigorously verified *dual lower bound* above one certifies that this exact
    affine/convex class cannot enter the requested target. The status and primal
    point returned here are candidate numerical evidence only.
    """
    if cp is None:
        raise RuntimeError(
            "CVXPY is not installed. Install cvxpy plus a conic solver, then rerun."
        )

    validate_spec(spec)
    nq = int(spec["parameter_dimension"])
    q = cp.Variable(nq, name="q")
    t = cp.Variable(name="target_scale")
    c = spec["constraints"]
    constraints: List[Any] = []
    named_constraints: List[tuple[str, Any]] = []

    def add(name: str, constraint: Any) -> None:
        constraints.append(constraint)
        named_constraints.append((name, constraint))

    add("target_scale_nonnegative", t >= 0)

    E = np.asarray(spec.get("equalities", {}).get("E", []), dtype=float)
    f = np.asarray(spec.get("equalities", {}).get("f", []), dtype=float).reshape(-1)
    if E.size:
        E = E.reshape(f.size, nq)
        add("generic_equalities", E @ q == f)

    G = np.asarray(spec.get("inequalities", {}).get("G", []), dtype=float)
    h = np.asarray(spec.get("inequalities", {}).get("h", []), dtype=float).reshape(-1)
    if G.size:
        G = G.reshape(h.size, nq)
        add("generic_inequalities", G @ q <= h)

    u_max = float(c["u_max"])
    slew_max = float(c["slew_max"])
    target_d = float(c["target_r_d"])
    target_cross = float(c["target_r_cross"])

    scenarios = [AffineScenario.from_dict(s, nq) for s in spec["scenarios"]]
    for s in scenarios:
        y_d = s.a_d + s.F_d @ q
        y_cross = s.a_cross + s.F_cross @ q
        u = s.a_u + s.F_u @ q
        du = s.a_slew + s.F_slew @ q

        add(
            f"{s.name}.differential_norm",
            cp.norm(y_d, 2) <= t * target_d * s.denom_d,
        )
        add(
            f"{s.name}.cross_norm",
            cp.norm(y_cross, 2) <= t * target_cross * s.denom_cross,
        )
        add(f"{s.name}.action_upper", u <= u_max)
        add(f"{s.name}.action_lower", -u <= u_max)
        add(f"{s.name}.slew_upper", du <= slew_max)
        add(f"{s.name}.slew_lower", -du <= slew_max)

    problem = cp.Problem(cp.Minimize(t), constraints)
    kwargs: Dict[str, Any] = {"verbose": False}
    if solver is not None:
        kwargs["solver"] = solver
    value = problem.solve(**kwargs)

    q_value = None if q.value is None else np.asarray(q.value, dtype=float).reshape(-1)
    t_value = None if t.value is None else float(t.value)

    dual_values: Dict[str, Any] = {}
    modeling_layer_violations: Dict[str, Any] = {}
    for name, constraint in named_constraints:
        dual_values[name] = _jsonable(getattr(constraint, "dual_value", None))
        try:
            violation = np.asarray(constraint.violation(), dtype=float)
            modeling_layer_violations[name] = _max_or_zero(np.abs(violation))
        except Exception:
            modeling_layer_violations[name] = None

    independent_primal_check = None
    if q_value is not None and t_value is not None:
        independent_primal_check = verify_margin_candidate(spec, q_value, t_value)

    return {
        "status": problem.status,
        "objective": None if value is None else float(value),
        "q": None if q_value is None else q_value.tolist(),
        "target_scale": t_value,
        "modeling_layer_constraint_violations": modeling_layer_violations,
        "constraint_dual_values": dual_values,
        "independent_primal_check": independent_primal_check,
        "solver_stats": {
            "solver_name": getattr(problem.solver_stats, "solver_name", None),
            "solve_time": getattr(problem.solver_stats, "solve_time", None),
            "num_iters": getattr(problem.solver_stats, "num_iters", None),
            "extra_stats": _jsonable(getattr(problem.solver_stats, "extra_stats", None)),
        },
        "warning": (
            "This is a candidate numerical result. The listed constraint dual values are "
            "not automatically an independently verified dual objective or Farkas ray. "
            "Export canonical conic data and verify stationarity, dual-cone membership, "
            "and a strict lower-bound/separation margin before making a theorem claim."
        ),
    }


def in_product_cone(
    z: np.ndarray, nonnegative: int, soc_sizes: Sequence[int], tol: float
) -> bool:
    """Check membership in ``R_+^m x SOC(k1) x ...``."""
    z = np.asarray(z, dtype=float).reshape(-1)
    expected = nonnegative + sum(soc_sizes)
    if z.size != expected:
        raise ValueError(f"cone vector has length {z.size}; expected {expected}")
    if nonnegative and np.min(z[:nonnegative]) < -tol:
        return False
    offset = nonnegative
    for size in soc_sizes:
        if size < 2:
            raise ValueError("each SOC block must have size at least 2")
        block = z[offset : offset + size]
        if block[0] + tol < np.linalg.norm(block[1:]):
            return False
        offset += size
    return True


def verify_conic_farkas(
    A: np.ndarray,
    b: np.ndarray,
    G: np.ndarray,
    h: np.ndarray,
    y: np.ndarray,
    z: np.ndarray,
    *,
    nonnegative: int,
    soc_sizes: Sequence[int],
    tol: float = 1e-8,
) -> Dict[str, Any]:
    """Verify a Farkas certificate for a product-cone feasibility problem.

    The primal convention is

    ``find x,s such that A x = b, G x + s = h, s in K``.

    A valid certificate satisfies ``A.T y + G.T z = 0``, ``z in K*``, and
    ``b.T y + h.T z < 0``. The supported nonnegative/SOC product cone is
    self-dual.
    """
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float).reshape(-1)
    G = np.asarray(G, dtype=float)
    h = np.asarray(h, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    z = np.asarray(z, dtype=float).reshape(-1)

    if A.shape[0] != b.size or A.shape[0] != y.size:
        raise ValueError("A, b, and y dimensions are inconsistent")
    if G.shape[0] != h.size or G.shape[0] != z.size:
        raise ValueError("G, h, and z dimensions are inconsistent")
    if A.shape[1] != G.shape[1]:
        raise ValueError("A and G must have the same number of primal columns")

    stationarity = A.T @ y + G.T @ z
    separation = float(b @ y + h @ z)
    cone_ok = in_product_cone(z, nonnegative, soc_sizes, tol)
    stationarity_norm = float(np.linalg.norm(stationarity, ord=np.inf))
    valid = cone_ok and stationarity_norm <= tol and separation < -tol
    return {
        "valid": bool(valid),
        "tolerance": float(tol),
        "stationarity_inf_norm": stationarity_norm,
        "dual_cone_membership": bool(cone_ok),
        "separation_value": separation,
        "strict_separation_margin": float(-separation),
        "required": "stationarity <= tol, z in K*, separation < -tol",
    }


def verify_lp_farkas(
    A: np.ndarray, b: np.ndarray, y: np.ndarray, tol: float = 1e-10
) -> Dict[str, Any]:
    """Verify ``Ax <= b`` infeasibility via ``y>=0, y.T A=0, y.T b<0``."""
    A = np.asarray(A, dtype=float)
    b = np.asarray(b, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if A.shape[0] != b.size or b.size != y.size:
        raise ValueError("A, b, and y dimensions are inconsistent")
    y_nonnegative = bool(np.min(y) >= -tol) if y.size else True
    stationarity = float(np.linalg.norm(y @ A, ord=np.inf))
    separation = float(y @ b)
    return {
        "tolerance": float(tol),
        "y_nonnegative": y_nonnegative,
        "yT_A_inf_norm": stationarity,
        "yT_b": separation,
        "strict_separation_margin": float(-separation),
        "valid": bool(y_nonnegative and stationarity <= tol and separation < -tol),
    }


def load_and_verify_conic_farkas(path: Path) -> Dict[str, Any]:
    """Load the independent-certificate JSON schema and verify it."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    return verify_conic_farkas(
        np.asarray(raw["A"], dtype=float),
        np.asarray(raw["b"], dtype=float),
        np.asarray(raw["G"], dtype=float),
        np.asarray(raw["h"], dtype=float),
        np.asarray(raw["y"], dtype=float),
        np.asarray(raw["z"], dtype=float),
        nonnegative=int(raw.get("nonnegative", 0)),
        soc_sizes=[int(v) for v in raw.get("soc_sizes", [])],
        tol=float(raw.get("tolerance", 1e-8)),
    )


def synthetic_lp_demo() -> Dict[str, Any]:
    """Return a tiny exact target-margin and Farkas demonstration.

    The synthetic constraints are ``|1.2-q| <= 0.95t`` and
    ``|1.2+q| <= 0.95t``. Their optimum is ``t*=24/19>1``. At ``t<=1``, two
    inequalities reduce to ``-q<=-1/4`` and ``q<=-1/4``. The multiplier
    ``y=(1,1)`` gives the exact contradiction ``0<=-1/2``.
    """
    A_ub = np.array(
        [
            [-1.0, -0.95],  # 1.2-q <= 0.95 t
            [1.0, -0.95],  # 1.2+q <= 0.95 t
            [1.0, -0.95],  # -(1.2-q) <= 0.95 t
            [-1.0, -0.95],  # -(1.2+q) <= 0.95 t
        ]
    )
    b_ub = np.array([-1.2, -1.2, 1.2, 1.2])
    c = np.array([0.0, 1.0])
    lp = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=[(None, None), (0.0, None)],
        method="highs",
    )

    A_target = np.array([[-1.0], [1.0]])
    b_target = np.array([-0.25, -0.25])
    y = np.array([1.0, 1.0])
    cert = verify_lp_farkas(A_target, b_target, y)

    return {
        "notice": "Synthetic certificate demonstration; not a VSG feasibility result.",
        "margin_lp_success": bool(lp.success),
        "margin_lp_status": int(lp.status),
        "q_star": None if not lp.success else float(lp.x[0]),
        "t_star_numeric": None if not lp.success else float(lp.x[1]),
        "t_star_exact": str(Fraction(24, 19)),
        "target_t_le_1_farkas": cert,
        "exact_certificate": {
            "A": [[-1], [1]],
            "b": ["-1/4", "-1/4"],
            "y": [1, 1],
            "yT_A": [0],
            "yT_b": "-1/2",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, help="Affine-map JSON specification")
    parser.add_argument("--solver", type=str, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--verify-farkas",
        type=Path,
        help="Independent product-cone Farkas certificate JSON",
    )
    parser.add_argument(
        "--synthetic-demo",
        action="store_true",
        help="Run the exact synthetic LP/Farkas demonstration.",
    )
    args = parser.parse_args()

    modes = int(args.synthetic_demo) + int(args.spec is not None) + int(
        args.verify_farkas is not None
    )
    if modes != 1:
        parser.error("choose exactly one of --spec, --verify-farkas, or --synthetic-demo")

    if args.synthetic_demo:
        result = synthetic_lp_demo()
    elif args.verify_farkas is not None:
        result = load_and_verify_conic_farkas(args.verify_farkas)
    else:
        assert args.spec is not None
        spec = load_spec(args.spec)
        result = solve_margin_socp(spec, solver=args.solver)

    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


