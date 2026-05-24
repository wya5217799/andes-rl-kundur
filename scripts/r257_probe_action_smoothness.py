"""R257 probe (no env/agent change) — action-smoothness / jitter hypothesis.

Follows R256 / CLM-0470: action-bound saturation REFUTED; over-actuation
identified (RL mean|dD|=563 vs droop k=10 mean|dD|=421). R255 mechanism
candidate 2 (anticipation lack / action jitter) is the natural follow-up:
is the issue not just magnitude but also choppiness?

Tests:
- mean per-step action change `|delta_M[t] - delta_M[t-1]|` (dM jitter)
- mean per-step action change `|delta_D[t] - delta_D[t-1]|` (dD jitter)
- total variation TV_M = sum |Δ| / n_steps (per-agent average)
- transient (t <= 5s) vs steady-state (t >= 25s) jitter

V4 action bounds: delta_M, delta_D in [-200, +600] (per andes_vsg_env_v4.py:122-125,
NOT the stale base_env.py:54-59 defaults — see CLM-0470 side-finding for the
documentation gap).

Hypothesis test (CLM-0470 R258 routing):
- RL chop > 2× droop k=10 → LAMBDA_SMOOTH > 0 motivated (R258A)
- RL chop <= 1.5× droop k=10 → magnitude penalty motivated (R258B)
- 1.5× < RL chop <= 2× droop → run both R258A and R258B

No env / agent / config touched. Read-only.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

DM_RANGE = 800.0  # = 600 - (-200), full bound span for normalized jitter
DD_RANGE = 800.0

TRANSIENT_END_S = 5.0
STEADY_START_S = 25.0


CONTROLLERS = [
    {
        "label": "R201_hreg_SOTA",
        "kind": "RL",
        "geo_role": "geo-best RL",
        "trace": ROOT
        / "results/r201_w1_hreg_tau005_s54/final_eval/final_eval_r201_w1_hreg_tau005_s54_load_step_1.json",
    },
    {
        "label": "R254_phif_only",
        "kind": "RL",
        "geo_role": "cum_rf-best RL among phi_f variants",
        "trace": ROOT
        / "results/r254_w1_scalar_phif_only_s50/final_eval/final_eval_r254_w1_scalar_phif_only_s50_load_step_1.json",
    },
    {
        "label": "R246_only_phi_abs",
        "kind": "RL",
        "geo_role": "cum_rf-worst RL",
        "trace": ROOT
        / "results/r246_w1_scalar_onlyphiabs_s50/final_eval/final_eval_r246_w1_scalar_onlyphiabs_s50_load_step_1.json",
    },
    {
        "label": "droop_k10",
        "kind": "classical",
        "geo_role": "cum_rf-best classical",
        "trace": ROOT / "results/r85_classical_baseline/scan_droop/k10.0/droop_load_step_1.json",
    },
    {
        "label": "droop_k2",
        "kind": "classical",
        "geo_role": "geo-best classical",
        "trace": ROOT / "results/r85_classical_baseline/scan_droop/k2.0/droop_load_step_1.json",
    },
    {
        "label": "no_control",
        "kind": "passive",
        "geo_role": "passive baseline",
        "trace": ROOT
        / "results/r85_classical_baseline/_no_control_cache/no_control_load_step_1.json",
    },
]


def smoothness_stats(arr: np.ndarray, time: np.ndarray) -> dict[str, float]:
    """
    arr: (n_steps, n_agents). Compute step-to-step diff -> stats.
    time: (n_steps,). For transient / steady masks.
    """
    if arr.shape[0] < 2:
        return {"mean_abs_jitter": 0.0, "max_abs_jitter": 0.0, "tv_per_step": 0.0,
                "transient_mean_jitter": 0.0, "steady_mean_jitter": 0.0,
                "p95_abs_jitter": 0.0}
    diffs = np.abs(np.diff(arr, axis=0))  # (n-1, n_agents)
    # Time index of each diff is the *later* step's time (so t[1:])
    t_diff = time[1:]
    transient_mask = t_diff <= TRANSIENT_END_S
    steady_mask = t_diff >= STEADY_START_S
    return {
        "mean_abs_jitter": float(np.mean(diffs)),
        "max_abs_jitter": float(np.max(diffs)),
        "p95_abs_jitter": float(np.percentile(diffs, 95)),
        # Total variation per agent per step (rough)
        "tv_per_step": float(np.mean(diffs)),
        "transient_mean_jitter": (
            float(np.mean(diffs[transient_mask]))
            if transient_mask.any()
            else 0.0
        ),
        "steady_mean_jitter": (
            float(np.mean(diffs[steady_mask])) if steady_mask.any() else 0.0
        ),
        # Sum of absolute changes across whole trajectory (per-agent mean)
        "total_variation": float(np.mean(np.sum(diffs, axis=0))),
    }


def analyse(trace_path: Path, label: str) -> dict[str, Any]:
    if not trace_path.exists():
        return {"label": label, "error": f"missing file: {trace_path}"}
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces = data["traces"]
    n_steps = len(traces)
    t = np.array([s["t"] for s in traces])
    dM = np.array([s["delta_M"] for s in traces])
    dD = np.array([s["delta_D"] for s in traces])

    M_stats = smoothness_stats(dM, t)
    D_stats = smoothness_stats(dD, t)

    return {
        "label": label,
        "n_steps": n_steps,
        "n_agents": dM.shape[1],
        "M_mean_jitter": M_stats["mean_abs_jitter"],
        "M_max_jitter": M_stats["max_abs_jitter"],
        "M_p95_jitter": M_stats["p95_abs_jitter"],
        "M_transient_jitter": M_stats["transient_mean_jitter"],
        "M_steady_jitter": M_stats["steady_mean_jitter"],
        "M_total_variation": M_stats["total_variation"],
        "D_mean_jitter": D_stats["mean_abs_jitter"],
        "D_max_jitter": D_stats["max_abs_jitter"],
        "D_p95_jitter": D_stats["p95_abs_jitter"],
        "D_transient_jitter": D_stats["transient_mean_jitter"],
        "D_steady_jitter": D_stats["steady_mean_jitter"],
        "D_total_variation": D_stats["total_variation"],
        # Normalized to bound span (for cross-controller comparison)
        "M_mean_jitter_norm": M_stats["mean_abs_jitter"] / DM_RANGE,
        "D_mean_jitter_norm": D_stats["mean_abs_jitter"] / DD_RANGE,
    }


def main() -> None:
    print("R257 probe: action-smoothness / jitter across cum_rf Pareto frontier")
    print("V4 bounds: dM, dD in [-200, +600]; jitter = |delta[t] - delta[t-1]|")
    print(f"Transient window: t <= {TRANSIENT_END_S}s | Steady: t >= {STEADY_START_S}s\n")

    results = [
        {**analyse(c["trace"], c["label"]), "kind": c["kind"], "geo_role": c["geo_role"]}
        for c in CONTROLLERS
    ]

    print("=== Delta_M jitter (inertia action change rate) ===")
    h = (
        f"{'Controller':<22} {'kind':<10} "
        f"{'mean':>8} {'p95':>8} {'max':>8} {'TV':>9} "
        f"{'tr_mean':>8} {'st_mean':>8}"
    )
    print(h)
    print("-" * len(h))
    for r in results:
        if "error" in r:
            print(f"{r['label']:<22} ERROR: {r['error']}")
            continue
        print(
            f"{r['label']:<22} {r['kind']:<10} "
            f"{r['M_mean_jitter']:>8.2f} {r['M_p95_jitter']:>8.2f} "
            f"{r['M_max_jitter']:>8.2f} {r['M_total_variation']:>9.1f} "
            f"{r['M_transient_jitter']:>8.2f} {r['M_steady_jitter']:>8.2f}"
        )

    print("\n=== Delta_D jitter (damping action change rate) ===")
    print(h)
    print("-" * len(h))
    for r in results:
        if "error" in r:
            continue
        print(
            f"{r['label']:<22} {r['kind']:<10} "
            f"{r['D_mean_jitter']:>8.2f} {r['D_p95_jitter']:>8.2f} "
            f"{r['D_max_jitter']:>8.2f} {r['D_total_variation']:>9.1f} "
            f"{r['D_transient_jitter']:>8.2f} {r['D_steady_jitter']:>8.2f}"
        )

    # Decision routing summary
    print("\n=== Decision routing (relative to droop k=10) ===")
    droop_k10 = next(
        (r for r in results if r["label"] == "droop_k10" and "error" not in r), None
    )
    if droop_k10 is None or droop_k10["D_mean_jitter"] == 0:
        print("droop_k10 baseline missing or zero-jitter; cannot compute relative")
    else:
        baseline_M = max(droop_k10["M_mean_jitter"], 1e-9)
        baseline_D = max(droop_k10["D_mean_jitter"], 1e-9)
        print(f"droop_k10 baseline: mean|dAm|={droop_k10['M_mean_jitter']:.2f}, "
              f"mean|dAd|={droop_k10['D_mean_jitter']:.2f}")
        print(f"{'Controller':<22} {'M_ratio':>9} {'D_ratio':>9}  routing")
        for r in results:
            if "error" in r or r["label"] == "droop_k10":
                continue
            m_ratio = r["M_mean_jitter"] / baseline_M if baseline_M > 1e-9 else float("inf")
            d_ratio = r["D_mean_jitter"] / baseline_D if baseline_D > 1e-9 else float("inf")
            # routing (RL only)
            if r["kind"] == "RL":
                if d_ratio > 2.0:
                    route = "SUPPORT - LAMBDA_SMOOTH motivated"
                elif d_ratio <= 1.5:
                    route = "REFUTE - magnitude not jitter"
                else:
                    route = "BORDERLINE 1.5x-2.0x"
            else:
                route = ""
            print(f"{r['label']:<22} {m_ratio:>9.2f} {d_ratio:>9.2f}  {route}")

    out = {
        "probe": "R257_action_smoothness_jitter",
        "bounds": {"DM_range": DM_RANGE, "DD_range": DD_RANGE},
        "transient_window_s": [0.0, TRANSIENT_END_S],
        "steady_window_s": [STEADY_START_S, 30.5],
        "controllers": results,
    }
    out_path = ROOT / "results/r257_probe_action_smoothness.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved: {out_path}")


if __name__ == "__main__":
    main()
