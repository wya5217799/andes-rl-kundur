"""R255 probe (10-min, no env change) — local-vs-global r_f mismatch hypothesis.

Tests CLM-0445's open mechanism question: is the RL cum_rf plateau
(-0.068 to -0.070 across R72/R201/R239/R174) caused by training r_f
using LOCAL-neighborhood-mean (3 agents out of 4 in Kundur ring)
while eval cum_rf uses GLOBAL-mean (all 4 agents)?

Approach: read existing trajectory JSONs for 4 controllers spanning
the Pareto frontier (R201 hreg SOTA, R254 phi_f-only, R246 only-phi_abs,
droop k=10) and compute BOTH per-step reward formulas. If RL converges
to local-r_f ≈ 0 while global-r_f stays > 0, the mismatch is real
and R255 env-change is justified.

Mechanism prediction:
- RL controllers (R201, R254, R246): local r_f trends to 0; global r_f
  stays nonzero (gap = local-vs-global mismatch).
- Droop k=10 (cum_rf-best): both local and global r_f small (symmetric
  controller doesn't exploit local-mean-can-hide drift).

Output: console table + json save. No env code touched.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

# Kundur 4-node ring: agent i sees self + COMM_ADJ[i] neighbors
COMM_ADJ = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}


def local_r_f(d_omega: np.ndarray) -> float:
    """Sum over agents of local-r_f penalty.

    For each agent i: omega_bar_i = mean(d_omega over self + COMM_ADJ[i]).
    r_f_i = -(d_omega[i] - omega_bar_i)^2 - sum_{j in COMM_ADJ[i]} (d_omega[j] - omega_bar_i)^2

    Mirrors base_env.py:680-682 exactly (assumes all comm links active,
    consistent with V4 default no-comm-fail).
    """
    total = 0.0
    for i, neighbors in COMM_ADJ.items():
        local_set = [i] + neighbors
        omega_bar = float(np.mean([d_omega[k] for k in local_set]))
        # Penalty contribution from agent i itself
        total += -(float(d_omega[i]) - omega_bar) ** 2
        # Penalty contribution from each active neighbor
        for j in neighbors:
            total += -(float(d_omega[j]) - omega_bar) ** 2
    return total


def global_r_f(d_omega: np.ndarray) -> float:
    """Paper Sec.IV-C cum_rf per-step contribution.

    -sum_i (d_omega[i] - global_mean)^2.

    Mirrors paper_strict_eval.compute_global_cum_rf per-step term.
    """
    global_mean = float(np.mean(d_omega))
    return -float(np.sum((d_omega - global_mean) ** 2))


def analyse_trajectory(trace_path: Path, label: str) -> dict:
    """Read a final_eval / classical-baseline trajectory JSON and
    compute time-integrated local-r_f vs global-r_f."""
    data = json.loads(trace_path.read_text(encoding="utf-8"))
    traces = data["traces"]
    n = len(traces)
    # delta_f_es is per-agent Δf in Hz, paper §IV-C uses the same
    df = np.array([s["delta_f_es"] for s in traces])  # (n, 4) Hz
    local_int = 0.0
    global_int = 0.0
    last_local = 0.0
    last_global = 0.0
    for k in range(n):
        d_omega = df[k]
        loc = local_r_f(d_omega)
        glo = global_r_f(d_omega)
        local_int += loc
        global_int += glo
        last_local = loc
        last_global = glo
    return {
        "label": label,
        "scenario": data.get("scenario", trace_path.stem),
        "n_steps": n,
        "local_r_f_integral": local_int,
        "global_r_f_integral": global_int,
        "ratio_global_over_local": (
            global_int / local_int if abs(local_int) > 1e-12 else float("nan")
        ),
        "last_step_local": last_local,
        "last_step_global": last_global,
        "max_df_overall": float(np.max(np.abs(df))),
    }


# Controllers spanning the dual-metric Pareto frontier
CONFIGS = [
    # (label, trajectory_path_relative_to_results)
    ("R201 hreg SOTA (geo-best)",
     "r201_w1_hreg_tau005_s54/final_eval/final_eval_r201_w1_hreg_tau005_s54_load_step_1.json"),
    ("R254 phi_f-only (RL minimal)",
     "r254_w1_scalar_phif_only_s50/final_eval/final_eval_r254_w1_scalar_phif_only_s50_load_step_1.json"),
    ("R246 only-phi_abs (no paper terms)",
     "r246_w1_scalar_onlyphiabs_s50/final_eval/final_eval_r246_w1_scalar_onlyphiabs_s50_load_step_1.json"),
    ("Droop k=10 (cum_rf-best)",
     "r85_classical_baseline/scan_droop/k10.0/droop_load_step_1.json"),
    ("Droop k=2 (geo-best classical)",
     "r85_classical_baseline/scan_droop/k2.0/droop_load_step_1.json"),
    ("No-control",
     "r85_classical_baseline/scan_droop/k10.0/no_control_load_step_1.json"),
]


def main() -> None:
    print("=== R255 probe: local vs global r_f integral (LS1 scenario) ===")
    print("Hypothesis: RL controllers minimize local r_f (training reward)")
    print("           but leave nonzero global r_f (eval cum_rf metric)")
    print("           because Kundur ring topology hides drift in local mean.\n")
    print(f"  {'controller':40s}  {'local r_f':>11s}  {'global r_f':>11s}  "
          f"{'gap %':>7s}  {'last local':>10s}  {'last global':>11s}")
    rows = []
    for label, rel in CONFIGS:
        p = ROOT / "results" / rel
        if not p.exists():
            print(f"  {label:40s}  (file missing: {rel})")
            continue
        r = analyse_trajectory(p, label)
        rows.append(r)
        gap_pct = 100.0 * (r["global_r_f_integral"] - r["local_r_f_integral"]) / \
                  abs(r["local_r_f_integral"]) if abs(r["local_r_f_integral"]) > 1e-9 else 0.0
        print(f"  {label:40s}  {r['local_r_f_integral']:>+11.4f}  "
              f"{r['global_r_f_integral']:>+11.4f}  {gap_pct:>+7.1f}  "
              f"{r['last_step_local']:>+10.4e}  {r['last_step_global']:>+11.4e}")
    out = ROOT / "results" / "r255_probe_local_vs_global_rf.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\n-> wrote {out}")

    # Interpretation
    print("\n=== Interpretation ===")
    print("If RL rows show |local| << |global|: training reward is misaligned")
    print("with eval metric → R255 env-change (global r_f scope) justified.")
    print("If RL rows show |local| ≈ |global|: ring topology hides nothing,")
    print("RL cum_rf plateau has a different mechanism → R255 hypothesis refuted.")


if __name__ == "__main__":
    main()
