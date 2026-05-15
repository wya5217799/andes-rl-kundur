"""Per-agent contribution analyzer — does each of 4 ESS contribute meaningfully?

Reads trace JSONs from eval_v4_baseline/ and computes per-agent metrics:
- ΔH range (max - min over episode) → does agent k actively change inertia?
- ΔD range → damping change activity
- ΔP_es swing (max abs change) → contribution to active power response
- Time-avg |ΔH|, |ΔD|, |ΔP_es|

Compares paper expectation (Fig.7/8): ES2 (Bus 16) dominates LS1, ES3 (Bus 14) dominates LS2.

Usage: python scripts/research_loop/analyze_per_agent_contribution.py [--labels lbl1 lbl2 ...]
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"

ES_NAMES = ["ES1 (Bus12)", "ES2 (Bus16)", "ES3 (Bus14)", "ES4 (Bus15)"]


def analyze(label: str, scen: str) -> dict | None:
    p = EVAL_DIR / f"{label}_{scen}.json"
    if not p.exists():
        return None
    j = json.load(open(p))
    tr = j["traces"]
    if not tr:
        return None
    # Per-agent ΔH (action[0] mapped from delta_M / 2), ΔD (action[1])
    dM = np.array([s["delta_M"] for s in tr])  # shape (T, 4)
    dD = np.array([s["delta_D"] for s in tr])  # (T, 4)
    P  = np.array([s["delta_P_es"] for s in tr])  # (T, 4)
    P0 = P[0]
    dP = P - P0  # contribution to power swing

    res = {"label": label, "scen": scen, "T": len(tr), "agents": []}
    for k in range(4):
        res["agents"].append({
            "name": ES_NAMES[k],
            "dH_range":     float(dM[:, k].max() - dM[:, k].min()) / 2.0,  # ΔH = ΔM/2
            "dH_mean_abs":  float(np.mean(np.abs(dM[:, k] / 2.0))),
            "dH_final":     float(dM[-1, k] / 2.0),
            "dD_range":     float(dD[:, k].max() - dD[:, k].min()),
            "dD_mean_abs":  float(np.mean(np.abs(dD[:, k]))),
            "dD_final":     float(dD[-1, k]),
            "dP_max_abs":   float(np.max(np.abs(dP[:, k]))),
            "dP_mean_abs":  float(np.mean(np.abs(dP[:, k]))),
        })
    return res


def gini(values: list[float]) -> float:
    """Gini coefficient: 0 = perfectly equal, 1 = single agent does all."""
    if not values or sum(values) == 0:
        return 0.0
    v = sorted(values)
    n = len(v)
    cum = np.cumsum(v)
    return float((n + 1 - 2 * np.sum(cum) / cum[-1]) / n)


def report(label: str):
    print(f"\n{'='*80}")
    print(f"  {label}")
    print(f"{'='*80}")
    for scen, scen_lbl in [("load_step_1", "LS1 (Bus14 −2.48)"), ("load_step_2", "LS2 (Bus15 +1.88)")]:
        r = analyze(label, scen)
        if r is None:
            print(f"  {scen_lbl}: NO DATA")
            continue
        print(f"\n  {scen_lbl} (T={r['T']} steps):")
        print(f"  {'Agent':18s} | {'ΔH_range':>10s} | {'ΔH_avg|.|':>10s} | {'ΔD_range':>10s} | {'ΔD_avg|.|':>10s} | {'ΔP_max':>8s} | {'ΔP_avg':>8s}")
        print(f"  {'-'*100}")
        dH_ranges, dD_ranges, dP_max = [], [], []
        for a in r["agents"]:
            print(f"  {a['name']:18s} | {a['dH_range']:>10.3f} | {a['dH_mean_abs']:>10.3f} | "
                  f"{a['dD_range']:>10.3f} | {a['dD_mean_abs']:>10.3f} | "
                  f"{a['dP_max_abs']:>8.3f} | {a['dP_mean_abs']:>8.3f}")
            dH_ranges.append(a['dH_range'])
            dD_ranges.append(a['dD_range'])
            dP_max.append(a['dP_max_abs'])
        # Gini coefficients (inequality of contribution)
        print(f"\n  Gini (0=equal, 1=monopoly): "
              f"ΔH_range={gini(dH_ranges):.3f}, "
              f"ΔD_range={gini(dD_ranges):.3f}, "
              f"ΔP_max={gini(dP_max):.3f}")
        # Identify dominant agent
        dom_h = ES_NAMES[int(np.argmax(dH_ranges))]
        dom_d = ES_NAMES[int(np.argmax(dD_ranges))]
        dom_p = ES_NAMES[int(np.argmax(dP_max))]
        print(f"  Dominant: ΔH={dom_h}  ΔD={dom_d}  ΔP={dom_p}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--labels", nargs="+",
                   default=["no_control", "ddic_v4_h50_s49",
                            "ddic_v4_ens2_R21ws8_w9802",
                            "ddic_v4_ens2_R21ws8_w8515",
                            "ddic_v4_8_R21_best",
                            "ddic_v4_peraxis_R21h_ws8d"])
    args = p.parse_args()
    print(f"\n=== Per-agent contribution analysis (paper expects ES2 dominates LS1, ES3 dominates LS2) ===")
    for lbl in args.labels:
        report(lbl)
