"""R256 probe (10-min, no env change) — Action-bound saturation hypothesis.

Tests CLM-0445/CLM-0460 mechanism candidate #1: does R201 SOTA's
actor saturate at action bounds (±DM_MAX or ±DD_MAX), while droop
k=10 freely uses larger ΔP magnitudes? If yes, RL is action-bounded
and widened bounds (R257 follow-up) might close the cum_rf gap. If
no, ruled out — move to mechanism candidate #2 (anticipation lack).

Note: CLM-0195 (R195 widebound experiment) already showed that
widening DM/DD bounds REGRESSED the SOTA. This probe quantifies
whether the existing bounds are even being approached.

Action range (V4Config defaults):
- delta_M ∈ [-200, +600] (DM_MIN, DM_MAX)
- delta_D ∈ [-200, +600] (DD_MIN, DD_MAX)
- Asymmetric: upper bound > lower bound.

A "saturated" timestep at upper = delta_M ≥ 0.95 × DM_MAX = 570.
A "saturated" timestep at lower = delta_M ≤ 0.95 × DM_MIN = -190.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Default V4 action bounds (from v4_config.py)
DM_MIN, DM_MAX = -200.0, 600.0
DD_MIN, DD_MAX = -200.0, 600.0
SATURATION_FRAC = 0.95


def analyse_trajectory(trace_path: Path, label: str) -> dict:
    """Extract action statistics from a trajectory JSON.

    Each timestep has ``delta_M`` and ``delta_D`` per agent. We report:
    - peak magnitude over time × agent (max |delta_*|)
    - mean magnitude
    - 95th percentile magnitude
    - % time-agent-cells at >=SATURATION_FRAC of bound
    """
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces = data["traces"]
    n = len(traces)

    # Stack into (n, 4) arrays
    delta_M = np.array([s.get("delta_M", [0]*4) for s in traces])  # (n, 4)
    delta_D = np.array([s.get("delta_D", [0]*4) for s in traces])  # (n, 4)

    def stats(arr: np.ndarray, lower: float, upper: float, name: str) -> dict:
        sat_upper = (arr >= SATURATION_FRAC * upper).sum() / arr.size * 100
        sat_lower = (arr <= SATURATION_FRAC * lower).sum() / arr.size * 100
        return {
            f"{name}_peak": float(np.max(np.abs(arr))),
            f"{name}_mean_abs": float(np.mean(np.abs(arr))),
            f"{name}_p95_abs": float(np.percentile(np.abs(arr), 95)),
            f"{name}_pct_sat_upper": float(sat_upper),
            f"{name}_pct_sat_lower": float(sat_lower),
            f"{name}_pct_sat_total": float(sat_upper + sat_lower),
        }
    out = {
        "label": label,
        "scenario": data.get("scenario", trace_path.stem),
        "n_steps": n,
    }
    out.update(stats(delta_M, DM_MIN, DM_MAX, "delta_M"))
    out.update(stats(delta_D, DD_MIN, DD_MAX, "delta_D"))
    return out


CONFIGS = [
    # (label, trajectory_path_relative_to_results)
    ("R201 hreg SOTA (geo-best)",
     "r201_w1_hreg_tau005_s54/final_eval/final_eval_r201_w1_hreg_tau005_s54_load_step_1.json"),
    ("R254 phi_f-only (RL minimal recipe)",
     "r254_w1_scalar_phif_only_s50/final_eval/final_eval_r254_w1_scalar_phif_only_s50_load_step_1.json"),
    ("R246 only-phi_abs (no paper terms)",
     "r246_w1_scalar_onlyphiabs_s50/final_eval/final_eval_r246_w1_scalar_onlyphiabs_s50_load_step_1.json"),
    ("Droop k=10 (cum_rf-best classical)",
     "r85_classical_baseline/scan_droop/k10.0/droop_load_step_1.json"),
    ("Droop k=2 (geo-best classical)",
     "r85_classical_baseline/scan_droop/k2.0/droop_load_step_1.json"),
    ("No-control",
     "r85_classical_baseline/scan_droop/k10.0/no_control_load_step_1.json"),
]


def main() -> None:
    print("=== R256 probe: action-bound saturation (LS1 scenario) ===")
    print(f"Bounds: delta_M ∈ [{DM_MIN}, {DM_MAX}], delta_D ∈ [{DD_MIN}, {DD_MAX}]")
    print(f"Saturation threshold: >= {SATURATION_FRAC*100:.0f}% of bound magnitude.\n")
    print(f"  {'controller':40s}  "
          f"{'dM peak':>8s}  {'dM mean':>8s}  {'dM p95':>8s}  "
          f"{'dM sat%':>8s}  {'dD sat%':>8s}")
    rows = []
    for label, rel in CONFIGS:
        p = ROOT / "results" / rel
        if not p.exists():
            print(f"  {label:40s}  (file missing: {rel})")
            continue
        r = analyse_trajectory(p, label)
        rows.append(r)
        print(f"  {label:40s}  "
              f"{r['delta_M_peak']:>8.1f}  {r['delta_M_mean_abs']:>8.1f}  "
              f"{r['delta_M_p95_abs']:>8.1f}  "
              f"{r['delta_M_pct_sat_total']:>7.2f}%  "
              f"{r['delta_D_pct_sat_total']:>7.2f}%")
    out = ROOT / "results" / "r256_probe_action_bound_saturation.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\n-> wrote {out}")

    # Interpretation per pre-registered decision rule
    print("\n=== Interpretation (R256 plan decision rule) ===")
    rl_labels = {r["label"] for r in rows if "R201" in r["label"] or "R254" in r["label"] or "R246" in r["label"]}
    rl_sat_max = max((r["delta_M_pct_sat_total"] + r["delta_D_pct_sat_total"])
                     for r in rows if r["label"] in rl_labels)
    droop_sat = next((r["delta_M_pct_sat_total"] + r["delta_D_pct_sat_total"]
                      for r in rows if "Droop k=10" in r["label"]), 0.0)
    print(f"  Max RL saturation (any algo, dM+dD sum): {rl_sat_max:.2f}%")
    print(f"  Droop k=10 saturation: {droop_sat:.2f}%")
    if rl_sat_max > 5.0:
        print("  → mechanism SUPPORTED (RL hits bounds >5% of time)")
        print("  → R257 candidate: train with widened bounds")
    elif rl_sat_max < 1.0:
        print("  → mechanism REFUTED (RL barely touches bounds)")
        print("  → move to mechanism #2 (anticipation lack) for next probe")
    else:
        print("  → borderline (1-5%); read trajectory shapes to disambiguate")


if __name__ == "__main__":
    main()
