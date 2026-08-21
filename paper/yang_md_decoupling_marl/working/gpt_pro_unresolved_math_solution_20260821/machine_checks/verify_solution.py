#!/usr/bin/env python3
"""Recompute the decision-bearing numerical claims in the U1--U9 solution.

Usage:
    python verify_solution.py --source /path/to/gpt_pro_unresolved_math_pack_20260821 \
        --output derived_results.json --verify-hashes

The script intentionally does not fabricate the missing Object-B sampled matrices or a
Youla/SLS certificate. It verifies what is actually identifiable from the supplied pack.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
try:
    from scipy.stats import beta as beta_dist
except Exception:  # pragma: no cover - optional only for the illustrative U9 interval table
    beta_dist = None


def read_json(root: Path, rel: str) -> Any:
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_hashes(root: Path) -> dict[str, Any]:
    sums = root / "SHA256SUMS"
    if not sums.is_file():
        return {"available": False, "checked": 0, "failures": ["SHA256SUMS missing"]}
    failures: list[str] = []
    checked = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        expected, rel = line.split(maxsplit=1)
        rel = rel.lstrip("*")
        path = root / rel
        if not path.is_file():
            failures.append(f"missing: {rel}")
            continue
        actual = sha256(path)
        checked += 1
        if actual != expected:
            failures.append(f"sha256 mismatch: {rel}")
    return {"available": True, "checked": checked, "failures": failures, "valid": not failures}


def cp_interval(k: int, n: int, alpha: float = 0.05) -> tuple[float, float] | None:
    if beta_dist is None:
        return None
    lower = 0.0 if k == 0 else float(beta_dist.ppf(alpha / 2.0, k, n - k + 1))
    upper = 1.0 if k == n else float(beta_dist.ppf(1.0 - alpha / 2.0, k + 1, n - k))
    return lower, upper


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--verify-hashes", action="store_true")
    args = parser.parse_args()
    root = args.source.resolve()

    r446 = read_json(root, "results/research_loop/r446_md_authority_fd/formal_analysis.json")
    r447 = read_json(root, "results/research_loop/r447_p1_complex_response/formal_analysis.json")
    r449 = read_json(root, "results/research_loop/r449_p1_sensitivity/formal_analysis.json")
    r450 = read_json(root, "results/research_loop/r450_p2_delay_loop/formal_analysis.json")
    r453 = read_json(root, "results/research_loop/r453_m5_aggregate_repair/formal_analysis.json")
    r456 = read_json(root, "results/research_loop/r456_m1_dual_saturation/formal_analysis.json")
    matrices = read_json(root, "results/research_loop/r405_homogenization_gate/linearization_matrices.json")

    # U1: exact dimensions that are exported, and the numerical objects that are not.
    first_profile = next(iter(matrices["profiles"].values()))
    u1_dimensions = {
        "dae_dynamic_state_dim": len(first_profile["f_x"]),
        "dae_algebraic_dim": len(first_profile["g_y"]),
        "object_b_state_dim_from_r447": int(r447["state_dim"]),
        "object_b_control_columns": int(r447["control_cols"]),
        "object_b_disturbance_columns": int(r447["disturbance_cols"]),
        "object_b_output_rows": int(r447["output_rows"]),
        "proposed_strictly_causal_fir_order_H": 10,
        "proposed_differential_youla_free_coefficients": 10 * 3 * 3,
    }

    # U3: a minimal aliasing counterexample for the registered 0.25/component slew limit.
    slew = 0.25
    raw = 0.0
    v_plus = np.clip(1.0 + np.clip(raw - 1.0, -slew, slew), -1.0, 1.0)
    v_minus = np.clip(-1.0 + np.clip(raw + 1.0, -slew, slew), -1.0, 1.0)
    u3_alias = {
        "raw_action": raw,
        "previous_executed_actions": [1.0, -1.0],
        "executed_actions": [float(v_plus), float(v_minus)],
        "different_next_state_if_x_next_equals_executed_action": bool(v_plus != v_minus),
        "maximum_raw_executed_gap_from_opposite_boundary": 1.75,
    }

    # U4: sufficient (not necessary) common-cost budgets for each fixed evaluation profile.
    # The derivation assumes each of the six registered scenario records separately obeys
    # sum_t c_common(t) <= B, N=30, dt=.2, sigma_f=.15 Hz, sigma_rocof=1 Hz/s.
    profile_dir = root / "results/research_loop/r452_m5_all_candidate_pareto/profiles"
    sigma_f = 0.15
    sigma_r = 1.0
    dt = 0.2
    n_steps = 30
    common_harm = 0.03
    u4_profiles: dict[str, Any] = {}
    for name in ("eval_a", "eval_b", "eval_c", "eval_d"):
        data = read_json(root, f"results/research_loop/r452_m5_all_candidate_pareto/profiles/{name}.json")
        static = data["static"]
        records = int(static["record_count"])
        peak_limit = (1.0 + common_harm) * float(static["worst_unit_peak_hz"])
        rocof_limit = (1.0 + common_harm) * float(static["worst_rocof_hz_s"])
        iae_limit = (1.0 + common_harm) * float(static["common_frequency_iae_hz_s"])
        # From mean_i e_i^2/sigma_f^2, an individual device sample is <= 2*sigma_f*sqrt(B).
        b_peak = (peak_limit / (2.0 * sigma_f)) ** 2
        b_rocof = (rocof_limit / (2.0 * sigma_r)) ** 2
        # Per-record IAE <= dt*sigma_f*sqrt(N*B); sum over registered records.
        b_iae = (iae_limit / (records * dt * sigma_f * math.sqrt(n_steps))) ** 2
        u4_profiles[name] = {
            "record_count": records,
            "reference": {
                "common_iae_hz_s": float(static["common_frequency_iae_hz_s"]),
                "peak_hz": float(static["worst_unit_peak_hz"]),
                "rocof_hz_s": float(static["worst_rocof_hz_s"]),
            },
            "guard_limits": {"iae_hz_s": iae_limit, "peak_hz": peak_limit, "rocof_hz_s": rocof_limit},
            "sufficient_episode_budget_bounds": {
                "from_iae": b_iae,
                "from_peak": b_peak,
                "from_rocof": b_rocof,
                "all_three": min(b_iae, b_peak, b_rocof),
            },
        }
    u4_min_budget = min(v["sufficient_episode_budget_bounds"]["all_three"] for v in u4_profiles.values())

    # U6: endpoint threshold bracket and descriptive linear interpolation only.
    nl0 = float(r450["nonlinear"]["0"]["ratios"]["r_d"])
    nl1 = float(r450["nonlinear"]["1"]["ratios"]["r_d"])
    threshold = 0.95
    dt_delay = float(r450["linear_loop"]["sample_period_seconds"])
    interpolation = dt_delay * (threshold - nl0) / (nl1 - nl0)
    width = dt_delay
    bisection = {
        str(tol): int(math.ceil(math.log2(width / tol)))
        for tol in (0.1, 0.05, 0.025, 0.01, 0.005)
    }
    u6 = {
        "nonlinear_r_d": {k: float(v["ratios"]["r_d"]) for k, v in r450["nonlinear"].items()},
        "threshold": threshold,
        "crossing_bracket_seconds_under_continuity": [0.0, dt_delay],
        "linear_interpolation_seconds_hypothetical": interpolation,
        "additional_bisection_points_for_target_interval_width": bisection,
        "zero_delay_linear_nonlinear_relative_error": float(
            r450["classification"]["linear_nonlinear_zero_delay_relative_error"]
        ),
        "nonlinear_zero_delay_relative_margin_to_threshold": (threshold - nl0) / nl0,
        "linear_min_return_difference_sigma": {
            k: float(v) for k, v in r450["linear_loop"]["min_return_difference_sigma"].items()
        },
    }

    # U8: exact diagonal heterogeneity measures for all R405 profiles.
    td = np.array(
        [
            [0.5, 0.5, -0.5, -0.5],
            [1 / math.sqrt(2), -1 / math.sqrt(2), 0.0, 0.0],
            [0.0, 0.0, 1 / math.sqrt(2), -1 / math.sqrt(2)],
        ],
        dtype=float,
    )
    q = np.ones(4) / 2.0
    u8_profiles: dict[str, Any] = {}
    for name, data in matrices["profiles"].items():
        m = np.asarray(data["baseline_m0"], dtype=float)
        d = np.asarray(data["baseline_d0"], dtype=float)
        dm = float(np.linalg.norm(td @ np.diag(m) @ q))
        dd = float(np.linalg.norm(td @ np.diag(d) @ q))
        m_std = float(np.std(m, ddof=0))
        d_std = float(np.std(d, ddof=0))
        if not (math.isclose(dm, m_std, rel_tol=1e-12, abs_tol=1e-12) and math.isclose(dd, d_std, rel_tol=1e-12, abs_tol=1e-12)):
            raise AssertionError("projector heterogeneity does not match population std")
        u8_profiles[name] = {
            "M": m.tolist(),
            "D": d.tolist(),
            "mean_M": float(np.mean(m)),
            "mean_D": float(np.mean(d)),
            "delta_M_projector_norm": dm,
            "delta_D_projector_norm": dd,
            "cv_M": dm / float(np.mean(m)),
            "cv_D": dd / float(np.mean(d)),
        }

    # U9: exact finite-bank branch meanings and optional binomial intervals under an added IID assumption.
    u9_intervals: dict[str, Any] = {}
    for k in range(5):
        interval = cp_interval(k, 4)
        u9_intervals[str(k)] = None if interval is None else {"lower": interval[0], "upper": interval[1]}
    u9_branches = {
        str(branch): {
            str(k): (
                "NO-GUARD-CLEAN-TRANSFER" if branch in (1, 2) and k == 0
                else "GUARD-CLEAN-TRANSFER" if branch in (1, 2) and k >= 1
                else "FALLBACK-NO-WITNESS"
            )
            for k in range(5)
        }
        for branch in (1, 2, 3)
    }

    output = {
        "source_root": str(root),
        "source_hash_verification": verify_hashes(root) if args.verify_hashes else {"performed": False},
        "u1_dimensions_and_class_design": u1_dimensions,
        "u3_aliasing_counterexample": u3_alias,
        "u4_sufficient_common_budget_analysis": {
            "registered_training_budget": 3.0,
            "profiles": u4_profiles,
            "tightest_all_three_sufficient_budget": u4_min_budget,
            "note": "These bounds cover only common IAE/peak/RoCoF under the stated per-record assumptions; they do not constrain action RMS, TV, saturation, endpoint improvements, or validity.",
        },
        "u6_delay_endpoint_analysis": u6,
        "u8_heterogeneity_measures": u8_profiles,
        "u9_branch_verdicts": u9_branches,
        "u9_hypothetical_iid_95pct_clopper_pearson": u9_intervals,
        "sealed_evidence_recap": {
            "r446_verdict": r446["verdict"],
            "r446_max_first_order_column": max(v["max_abs"] for v in r446["per_column"].values()),
            "r447_energy_ratio": float(r447["energy_ratio_bandpass_over_local"]),
            "r449": r449["results"],
            "r453_guard_clean_ids": {k: v["joint_guard_feasible_ids"] for k, v in r453["profiles"].items()},
            "r456_rms_gradient_conflict_support_count": int(r456["mechanisms"]["gradient_conflict"]["rms"]["support_count"]),
            "r456_state_shards": int(r456["state_shards"]),
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "status": "ok"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
