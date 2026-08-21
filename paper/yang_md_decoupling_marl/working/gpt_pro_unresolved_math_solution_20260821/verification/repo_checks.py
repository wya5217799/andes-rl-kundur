"""Independent repository-side checks for the GPT Pro U1--U9 solution.

This is scratch verification, not evidence of a new physical experiment.  It
recomputes algebraic and combinatorial claims without importing the solution
package's checker.  Usage:

    python paper/yang_md_decoupling_marl/working/\
        gpt_pro_unresolved_math_solution_20260821/verification/repo_checks.py \
        --output paper/yang_md_decoupling_marl/working/\
        gpt_pro_unresolved_math_solution_20260821/verification/repo_checks.json

Failure mode: any failed invariant raises before the JSON is written.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm


def _find_repo_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "src/andes_rl_kundur").is_dir() and (
            candidate / "paper/yang_md_decoupling_marl"
        ).is_dir():
            return candidate
    raise RuntimeError(f"cannot locate repository root from {start}")


ROOT = _find_repo_root(Path(__file__).resolve().parent)
sys.path.insert(0, str(ROOT / "src"))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _zoh_integral(a: np.ndarray, b: np.ndarray, horizon: float) -> np.ndarray:
    n, m = b.shape
    block = np.block([[a, b], [np.zeros((m, n + m))]])
    return expm(block * horizon)[:n, n:]


def check_u1() -> dict[str, Any]:
    q = np.ones((4, 1)) / 2.0
    pc = q @ q.T
    pd = np.eye(4) - pc
    eigenvalues = np.linalg.eigvalsh(pd)
    rank = int(np.linalg.matrix_rank(pd, tol=1e-12))
    assert rank == 3
    assert np.allclose(pd @ pd, pd, atol=1e-14)
    return {
        "common_projector_rank": int(np.linalg.matrix_rank(pc)),
        "differential_projector_rank": rank,
        "differential_projector_eigenvalues": eigenvalues.tolist(),
        "ten_tap_free_coefficients": 10 * rank * rank,
        "scope": "class dimension only; no DCF, lift, primal witness, or dual certificate",
    }


def check_u2() -> dict[str, Any]:
    nodes = range(4)
    episodes = range(5)
    true_pairs: dict[str, list[tuple[int, int]]] = {"left": [], "right": []}
    placebo_pairs: dict[str, list[tuple[int, int]]] = {"left": [], "right": []}
    changed = []
    for i in nodes:
        for e in episodes:
            donor_episode = (e + 1) % 5
            true_left = ((i - 1) % 4, e)
            true_right = ((i + 1) % 4, e)
            placebo_left = (i, donor_episode)
            placebo_right = ((i + 2) % 4, donor_episode)
            true_pairs["left"].append(true_left)
            true_pairs["right"].append(true_right)
            placebo_pairs["left"].append(placebo_left)
            placebo_pairs["right"].append(placebo_right)
            changed.extend(
                [true_left[0] != placebo_left[0], true_right[0] != placebo_right[0]]
            )
    pooled_marginals_equal = {
        slot: Counter(true_pairs[slot]) == Counter(placebo_pairs[slot])
        for slot in ("left", "right")
    }
    assert all(changed)
    assert all(pooled_marginals_equal.values())
    return {
        "recipient_episode_cases": 4 * 5,
        "all_semantic_donor_nodes_changed": all(changed),
        "pooled_node_episode_marginals_equal": pooled_marginals_equal,
        "not_established": [
            "recipient-conditional equality",
            "joint temporal independence",
            "population intrinsic information value",
        ],
    }


def check_u3() -> dict[str, Any]:
    agent = _load_module(
        "repo_cd_matd3_for_gpt_pro_check",
        ROOT / "src/andes_rl_kundur/agents/cd_matd3.py",
    )
    import torch

    previous = torch.tensor([[1.0], [-1.0]], dtype=torch.float64)
    raw = torch.zeros_like(previous)
    executed = agent.project_slew_torch(previous, raw, slew_limit=0.25).numpy().reshape(-1)
    assert np.allclose(executed, [0.75, -0.75])
    return {
        "same_raw_action": 0.0,
        "previous_executed": [1.0, -1.0],
        "repo_executed_actions": executed.tolist(),
        "transition_alias_exists_without_previous_executed": bool(executed[0] != executed[1]),
    }


def check_u4() -> dict[str, Any]:
    sigma_f = 0.15
    sigma_rocof = 1.0
    dt = 0.2
    steps = 30
    harm = 0.03
    rows: dict[str, Any] = {}
    for profile in ("eval_a", "eval_b", "eval_c", "eval_d"):
        data = _read_json(
            ROOT
            / "results/research_loop/r452_m5_all_candidate_pareto/profiles"
            / f"{profile}.json"
        )["static"]
        records = int(data["record_count"])
        bounds = {
            "iae": (
                (1 + harm)
                * float(data["common_frequency_iae_hz_s"])
                / (records * dt * sigma_f * math.sqrt(steps))
            )
            ** 2,
            "peak": ((1 + harm) * float(data["worst_unit_peak_hz"]) / (2 * sigma_f))
            ** 2,
            "rocof": (
                (1 + harm) * float(data["worst_rocof_hz_s"]) / (2 * sigma_rocof)
            )
            ** 2,
        }
        rows[profile] = {**bounds, "all_three": min(bounds.values())}
    tightest = min(row["all_three"] for row in rows.values())
    bad_profile_probability = 0.01
    expected_cost_counterexample = (
        (1 - bad_profile_probability) * 0.0
        + bad_profile_probability * (3.0 / bad_profile_probability)
    )
    assert math.isclose(expected_cost_counterexample, 3.0)
    assert math.isclose(tightest, 0.0009421116622729003, rel_tol=1e-12)
    return {
        "per_record_assumption": "each 30-step scenario separately obeys the same undiscounted budget",
        "bounds": rows,
        "tightest_common_only_sufficient_budget": tightest,
        "registered_budget": 3.0,
        "registered_to_tightest_ratio": 3.0 / tightest,
        "expectation_counterexample_expected_cost": expected_cost_counterexample,
        "does_not_cover": [
            "endpoint improvements",
            "action RMS",
            "action TV",
            "saturation",
            "validity",
        ],
    }


def check_u5() -> dict[str, Any]:
    rng = np.random.default_rng(20260821)
    n, m, r, p = 3, 2, 2, 2
    a0 = rng.normal(scale=0.08, size=(n, n))
    a0 -= 0.4 * np.eye(n)
    ar = rng.normal(scale=0.02, size=(n, n))
    bc0 = rng.normal(scale=0.2, size=(n, m))
    bcr = rng.normal(scale=0.03, size=(n, m))
    bw0 = rng.normal(scale=0.2, size=(n, r))
    bwr = rng.normal(scale=0.03, size=(n, r))
    c0 = rng.normal(scale=0.2, size=(p, n))
    cr = rng.normal(scale=0.03, size=(p, n))
    dc0 = rng.normal(scale=0.01, size=(p, m))
    dcr = rng.normal(scale=0.002, size=(p, m))
    dw0 = rng.normal(scale=0.01, size=(p, r))
    dwr = rng.normal(scale=0.002, size=(p, r))
    k0 = rng.normal(scale=0.2, size=(m, p))
    kr = rng.normal(scale=0.02, size=(m, p))
    z = np.exp(0.37j)

    def values(rho: float) -> tuple[np.ndarray, ...]:
        a = a0 + rho * ar
        bc = bc0 + rho * bcr
        bw = bw0 + rho * bwr
        c = c0 + rho * cr
        dc = dc0 + rho * dcr
        dw = dw0 + rho * dwr
        k = k0 + rho * kr
        resolvent = np.linalg.inv(z * np.eye(n) - a)
        pc = c @ resolvent @ bc + dc
        pw = c @ resolvent @ bw + dw
        g = np.linalg.solve(np.eye(p) + pc @ k, pw)
        return a, bc, bw, c, dc, dw, k, g

    a, bc, bw, c, dc, dw, k, g = values(0.0)
    resolvent = np.linalg.inv(z * np.eye(n) - a)
    pc = c @ resolvent @ bc + dc
    pw = c @ resolvent @ bw + dw
    pc_r = cr @ resolvent @ bc + c @ resolvent @ ar @ resolvent @ bc + c @ resolvent @ bcr + dcr
    pw_r = cr @ resolvent @ bw + c @ resolvent @ ar @ resolvent @ bw + c @ resolvent @ bwr + dwr
    s = np.linalg.inv(np.eye(p) + pc @ k)
    g_r = s @ (pw_r - (pc_r @ k + pc @ kr) @ g)
    step = 1e-6
    fd = (values(step)[-1] - values(-step)[-1]) / (2 * step)
    relative_error = float(np.linalg.norm(g_r - fd) / np.linalg.norm(fd))
    assert relative_error < 1e-8
    return {
        "random_mimo_dimensions": {"state": n, "control": m, "disturbance": r, "output": p},
        "total_derivative_relative_error_vs_centered_difference": relative_error,
        "scope": "generic identity only; no Object-B total derivative was computed",
    }


def check_u6() -> dict[str, Any]:
    a = np.array([[-0.4, 0.2], [0.1, -0.3]])
    b = np.array([[1.0], [0.4]])
    ts = 0.2
    delta = 0.073
    full = _zoh_integral(a, b, ts)
    b0 = _zoh_integral(a, b, ts - delta)
    b1 = full - b0
    grid = np.linspace(0.0, ts, 200_001)
    integrand = np.stack([(expm(a * (ts - value)) @ b)[:, 0] for value in grid])
    old_mask = grid <= delta
    b1_quad = np.trapezoid(integrand[old_mask], grid[old_mask], axis=0)[:, None]
    b0_quad = np.trapezoid(integrand[~old_mask], grid[~old_mask], axis=0)[:, None]
    split_error = float(max(np.max(np.abs(b0 - b0_quad)), np.max(np.abs(b1 - b1_quad))))
    r0 = 0.9389467751129211
    r1 = 0.9502787797165233
    threshold = 0.95
    interpolation = ts * (threshold - r0) / (r1 - r0)
    assert split_error < 2e-6
    assert 0.0 < interpolation < ts
    return {
        "fractional_delay_seconds": delta,
        "zoh_split_quadrature_max_abs_error": split_error,
        "threshold_bracket_under_continuity_seconds": [0.0, ts],
        "linear_interpolation_seconds_descriptive_only": interpolation,
        "not_established": "pole-crossing or robust-stability delay margin",
    }


def check_u7() -> dict[str, Any]:
    # Scalar swing proxy: f(x,u,w)=(w-d*x)/(m+u).  The equilibrium residual is
    # zero for every nearby u, so pure-u derivatives vanish and mixed terms lead.
    m = 4.0
    d = 1.5
    h = 1e-5

    def field(x: float, u: float, w: float) -> float:
        return (w - d * x) / (m + u)

    pure_u_second = (field(0.0, h, 0.0) - 2 * field(0.0, 0.0, 0.0) + field(0.0, -h, 0.0)) / h**2
    mixed_xu = (
        field(h, h, 0.0)
        - field(h, -h, 0.0)
        - field(-h, h, 0.0)
        + field(-h, -h, 0.0)
    ) / (4 * h**2)
    expected_mixed_xu = d / m**2
    assert abs(pure_u_second) < 1e-12
    assert math.isclose(mixed_xu, expected_mixed_xu, rel_tol=2e-6)

    # Counterexample to the insufficient premise f_u(0)=0 by itself.
    def generic_field(u: float) -> float:
        return u**2

    generic_first = (generic_field(h) - generic_field(-h)) / (2 * h)
    generic_second = (generic_field(h) - 2 * generic_field(0.0) + generic_field(-h)) / h**2
    assert abs(generic_first) < 1e-12
    assert math.isclose(generic_second, 2.0, rel_tol=1e-12)
    return {
        "swing_proxy_pure_u_second_derivative": pure_u_second,
        "swing_proxy_mixed_x_u_derivative": mixed_xu,
        "swing_proxy_expected_mixed_x_u_derivative": expected_mixed_xu,
        "generic_counterexample": {"f_u_at_equilibrium": generic_first, "f_uu_at_equilibrium": generic_second},
        "required_added_assumption": (
            "the equilibrium output/vector field remains zero for every nearby M/D command "
            "within one fixed smooth active mode, eliminating pure action terms"
        ),
    }


def check_u8() -> dict[str, Any]:
    rng = np.random.default_rng(8)
    a = rng.normal(size=(4, 4)) - 2.0 * np.eye(4)
    q = np.ones((4, 1)) / 2.0
    p = q @ q.T
    r = np.linalg.inv(0.4j * np.eye(4) - a)
    commutator_error = float(np.max(np.abs((r @ p - p @ r) - r @ (a @ p - p @ a) @ r)))
    td = np.array(
        [
            [0.5, 0.5, -0.5, -0.5],
            [1 / math.sqrt(2), -1 / math.sqrt(2), 0.0, 0.0],
            [0.0, 0.0, 1 / math.sqrt(2), -1 / math.sqrt(2)],
        ]
    )
    m = np.array([140.0, 180.0, 220.0, 260.0])
    projector_norm = float(np.linalg.norm(td @ np.diag(m) @ q[:, 0]))
    population_std = float(np.std(m, ddof=0))
    assert commutator_error < 1e-12
    assert math.isclose(projector_norm, population_std, rel_tol=1e-12)
    return {
        "resolvent_commutator_max_abs_error": commutator_error,
        "heterogeneity_projector_norm": projector_norm,
        "population_standard_deviation": population_std,
        "scope": "identity and numerator only; no numerical R405 cross-transfer bound",
    }


def check_u9() -> dict[str, Any]:
    selection = _read_json(
        ROOT / "results/research_loop/r458_dev_select_eval_validate/selection.json"
    )
    branch = int(selection["selection_priority_branch"])
    assert branch in (1, 2, 3)
    verdicts = {
        str(b): {
            str(k): (
                "NO-GUARD-CLEAN-TRANSFER"
                if b in (1, 2) and k == 0
                else "GUARD-CLEAN-TRANSFER"
                if b in (1, 2) and k >= 1
                else "FALLBACK-NO-WITNESS"
            )
            for k in range(5)
        }
        for b in (1, 2, 3)
    }
    return {
        "actual_selection_branch": branch,
        "actual_winner": selection["winner"],
        "candidate_pool": selection["candidate_pool"],
        "branch_count_table": verdicts,
        "statistical_unit": "one fixed profile guard decision; K of four fixed profiles is descriptive",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = {
        "schema_version": 1,
        "authority": "scratch-independent-algebraic-and-repository-check",
        "u1": check_u1(),
        "u2": check_u2(),
        "u3": check_u3(),
        "u4": check_u4(),
        "u5": check_u5(),
        "u6": check_u6(),
        "u7": check_u7(),
        "u8": check_u8(),
        "u9": check_u9(),
    }
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
