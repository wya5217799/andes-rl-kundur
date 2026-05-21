"""R257 probe (10-min, no env change) — Anticipation-lag hypothesis.

Tests CLM-0470 mechanism candidate #2: does droop k=10 react INSTANTLY
to Δf changes (proportional control, zero lag) while RL has a learned
LAG (k≥1 steps) that delays response and contributes to the cum_rf
gap? If yes, RL's reactive (not anticipatory) policy is the issue;
if no, lag isn't the bottleneck.

Approach: per agent, compute lag-correlation between action change
Δaction[t] and disturbance change Δ|d_omega[t-k]| for k in {-2,-1,0,+1,+2}.
- Droop: should peak at k=0 (instant response).
- RL: if lag, peak shifts to k≥1 (action responds to PAST disturbance).
- If RL peak at k=0 same as droop: lag NOT the issue.

Operates on existing trajectory JSONs. No env / train / score touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def reaction_lag_analysis(trace_path: Path, label: str, lags: list[int]
                          ) -> dict:
    """For one trajectory, compute lag-correlation of action vs
    |d_omega| for each agent, then average across agents.

    Reports peak-lag (the k at which correlation is highest) and the
    correlation at k=0 (no-lag baseline)."""
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces = data["traces"]
    n = len(traces)
    if n < max(abs(k) for k in lags) + 2:
        return {"label": label, "error": "trajectory too short"}

    # (n, 4) arrays
    df = np.array([s["delta_f_es"] for s in traces])  # Δf per agent
    delta_D = np.array([s.get("delta_D", [0.0]*4) for s in traces])
    delta_M = np.array([s.get("delta_M", [0.0]*4) for s in traces])
    # Use the "scaled action magnitude" combining dM + dD as the
    # controller's reaction-action signal. For droop k=10 dM=0 → only dD.
    # For RL both contribute.
    action_mag = np.abs(delta_D) + np.abs(delta_M)
    disturbance_mag = np.abs(df)

    # For each agent, compute correlation of action_mag[t] with
    # disturbance_mag[t-k] for each k in lags. Positive k = "action
    # responds to past disturbance (lag)"; negative k = "action precedes
    # disturbance (anticipation)".
    per_agent_lags: dict[int, float] = {k: 0.0 for k in lags}
    n_agents = df.shape[1]
    for ai in range(n_agents):
        a = action_mag[:, ai] - action_mag[:, ai].mean()
        d = disturbance_mag[:, ai] - disturbance_mag[:, ai].mean()
        a_std = a.std() + 1e-12
        d_std = d.std() + 1e-12
        for k in lags:
            # action[t] vs disturbance[t-k] → shift disturbance by +k
            if k >= 0:
                a_seg = a[k:]
                d_seg = d[:n - k]
            else:
                a_seg = a[:n + k]
                d_seg = d[-k:]
            if len(a_seg) < 5:
                continue
            corr = float(np.mean(a_seg * d_seg) / (a_std * d_std))
            per_agent_lags[k] += corr / n_agents

    peak_k = max(per_agent_lags, key=lambda k: per_agent_lags[k])
    return {
        "label": label,
        "scenario": data.get("scenario", trace_path.stem),
        "n_steps": n,
        "corr_by_lag": per_agent_lags,
        "peak_lag": peak_k,
        "corr_at_peak": per_agent_lags[peak_k],
        "corr_at_zero": per_agent_lags[0],
    }


CONFIGS = [
    ("R201 hreg SOTA",
     "r201_w1_hreg_tau005_s54/final_eval/final_eval_r201_w1_hreg_tau005_s54_load_step_1.json"),
    ("R254 phi_f-only",
     "r254_w1_scalar_phif_only_s50/final_eval/final_eval_r254_w1_scalar_phif_only_s50_load_step_1.json"),
    ("R246 only-phi_abs",
     "r246_w1_scalar_onlyphiabs_s50/final_eval/final_eval_r246_w1_scalar_onlyphiabs_s50_load_step_1.json"),
    ("Droop k=10",
     "r85_classical_baseline/scan_droop/k10.0/droop_load_step_1.json"),
    ("Droop k=2",
     "r85_classical_baseline/scan_droop/k2.0/droop_load_step_1.json"),
]
LAGS = [-2, -1, 0, 1, 2]


def main() -> None:
    print("=== R257 probe: action-vs-disturbance lag correlation (LS1) ===")
    print("Positive k = action responds to disturbance from k steps ago (lag)")
    print("Negative k = action precedes disturbance (anticipation)")
    print("Peak at k=0 = instant proportional response (droop-style)\n")
    print(f"  {'controller':25s}  "
          + "  ".join(f"k={k:+d}" for k in LAGS)
          + "  peak_k  | corr_at_peak  corr_at_zero")
    rows = []
    for label, rel in CONFIGS:
        p = ROOT / "results" / rel
        if not p.exists():
            print(f"  {label:25s}  (missing)")
            continue
        r = reaction_lag_analysis(p, label, LAGS)
        rows.append(r)
        if "error" in r:
            print(f"  {label:25s}  {r['error']}")
            continue
        corr_str = "  ".join(f"{r['corr_by_lag'][k]:+5.3f}" for k in LAGS)
        print(f"  {label:25s}  {corr_str}  "
              f"k={r['peak_lag']:+d}    | {r['corr_at_peak']:+5.3f}        "
              f"{r['corr_at_zero']:+5.3f}")
    out = ROOT / "results" / "r257_probe_anticipation_lag.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\n-> wrote {out}")

    # Interpretation
    print("\n=== Interpretation ===")
    droop_peak = next((r['peak_lag'] for r in rows if 'Droop k=10' in r.get('label','')), None)
    rl_peaks = [r['peak_lag'] for r in rows if 'R201' in r.get('label','') or 'R254' in r.get('label','') or 'R246' in r.get('label','')]
    print(f"  Droop k=10 peak lag: {droop_peak}")
    print(f"  RL peak lags: {rl_peaks}")
    if droop_peak == 0 and all(p > 0 for p in rl_peaks if p is not None):
        print("  → mechanism SUPPORTED: RL lags droop by k≥1 step")
    elif droop_peak == 0 and all(p == 0 for p in rl_peaks if p is not None):
        print("  → mechanism REFUTED: RL and droop both respond at k=0")
    else:
        print("  → mixed; manual interpretation needed")


if __name__ == "__main__":
    main()
