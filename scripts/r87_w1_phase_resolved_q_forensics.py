"""R87-W1 — phase-resolved analysis of cached on-manifold Q-landscape probes.

Reads `results/r84_d2b_q_landscape_trajectory/per_step.json` (400 records,
4 agents × 2 scenarios × 50 steps from R84-W3-traj). CLM-0160 reported
overall median metrics; this script clusters by (phase, scenario, agent)
and surfaces any time-window where the critic loses on-manifold confidence.

Output: results/r87_w1_phase_resolved/{summary.json,
advantage_timeseries.png, per_phase_table.csv}.

Phase buckets:
    impulse:  step ∈ [0, 5)     (disturbance just applied)
    rising:   step ∈ [5, 15)    (frequency excursion still building)
    decaying: step ∈ [15, 30)   (active control, peak deviation)
    settling: step ∈ [30, 50]   (returning to nominal)
"""
from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]

CACHE = ROOT / "results" / "r84_d2b_q_landscape_trajectory" / "per_step.json"
OUT = ROOT / "results" / "r87_w1_phase_resolved"
OUT.mkdir(parents=True, exist_ok=True)


# Same thresholds as CLM-0160 / R84-D2b for compatibility.
ADVANTAGE_FAIL = 0.0
ARGMAX_DIST_FAIL_FRACTION = 0.5            # > 50% of action diagonal (~1.41)
ACTION_DIAGONAL = float(np.sqrt(8))         # max ||a1 - a2||_2 in [-1, 1]^2
ARGMAX_DIST_FAIL = ARGMAX_DIST_FAIL_FRACTION * ACTION_DIAGONAL


def phase_of(step: int) -> str:
    if step < 5:
        return "impulse"
    if step < 15:
        return "rising"
    if step < 30:
        return "decaying"
    return "settling"


def summarise(records: list[dict]) -> dict:
    if not records:
        return {"n": 0}
    arr_adv = np.array([r["advantage"] for r in records])
    arr_amx = np.array([r["argmax_dist"] for r in records])
    arr_q12 = np.array([r["q1q2_disagreement"] for r in records])
    arr_q_sota = np.array([r["q_sota_mean"] for r in records])
    arr_obs_n = np.array([r["obs_norm"] for r in records])
    return {
        "n": len(records),
        "advantage_median": float(np.median(arr_adv)),
        "advantage_p10":    float(np.percentile(arr_adv, 10)),
        "advantage_p90":    float(np.percentile(arr_adv, 90)),
        "advantage_pos_frac": float((arr_adv > 0).mean()),
        "argmax_dist_median": float(np.median(arr_amx)),
        "argmax_dist_p90": float(np.percentile(arr_amx, 90)),
        "argmax_dist_rel_diag_median": float(np.median(arr_amx) / ACTION_DIAGONAL),
        "q1q2_disagreement_median": float(np.median(arr_q12)),
        "q_sota_mean_median": float(np.median(arr_q_sota)),
        "obs_norm_median": float(np.median(arr_obs_n)),
    }


def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not CACHE.exists():
        sys.exit(f"FATAL: cached per_step.json missing at {CACHE}")
    records = json.loads(CACHE.read_text())
    print(f"loaded {len(records)} probe records")

    # ── 1. Per-phase × scenario × agent aggregate ──────────────────────
    by_phase: dict[tuple[str, str, int], list[dict]] = defaultdict(list)
    by_phase_global: dict[str, list[dict]] = defaultdict(list)
    by_step: dict[tuple[str, int], list[dict]] = defaultdict(list)
    by_step_global: dict[int, list[dict]] = defaultdict(list)
    by_agent: dict[int, list[dict]] = defaultdict(list)
    for r in records:
        ph = phase_of(r["step"])
        by_phase[(ph, r["scenario"], r["agent"])].append(r)
        by_phase_global[ph].append(r)
        by_step[(r["scenario"], r["step"])].append(r)
        by_step_global[r["step"]].append(r)
        by_agent[r["agent"]].append(r)

    per_phase_global = {ph: summarise(by_phase_global[ph]) for ph in
                          ("impulse", "rising", "decaying", "settling")}
    per_agent_global = {f"agent_{i}": summarise(by_agent[i]) for i in sorted(by_agent)}

    # CSV: phase × scenario × agent
    csv_rows: list[dict] = []
    for (ph, scen, ag), recs in sorted(by_phase.items()):
        s = summarise(recs)
        csv_rows.append({
            "phase": ph, "scenario": scen, "agent": ag,
            "n": s["n"],
            "advantage_median": round(s["advantage_median"], 5),
            "advantage_pos_frac": round(s["advantage_pos_frac"], 4),
            "argmax_dist_rel_diag_median": round(s["argmax_dist_rel_diag_median"], 4),
            "q1q2_disagreement_median": round(s["q1q2_disagreement_median"], 5),
        })
    with open(OUT / "per_phase_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        w.writeheader()
        w.writerows(csv_rows)

    # ── 2. Gate evaluation ──────────────────────────────────────────────
    phase_pass: dict[str, bool] = {}
    for ph, stats in per_phase_global.items():
        passes = (stats["advantage_median"] > ADVANTAGE_FAIL and
                   stats["argmax_dist_median"] < ARGMAX_DIST_FAIL)
        phase_pass[ph] = passes

    if all(phase_pass.values()):
        gate = "A_ALL_PHASES_PASS"
    elif phase_pass.get("settling", False) and not all(
            phase_pass.get(ph, False) for ph in ("impulse", "rising", "decaying")):
        gate = "B_TRANSIENT_FAIL_STEADY_PASS"
    elif not any(phase_pass.values()):
        gate = "C_ALL_PHASES_FAIL"
    else:
        gate = "D_MIXED"

    # ── 3. Correlations obs_norm ↔ critic metrics ───────────────────────
    obs_n = np.array([r["obs_norm"] for r in records])
    adv = np.array([r["advantage"] for r in records])
    amx = np.array([r["argmax_dist"] for r in records])
    q_sota = np.array([r["q_sota_mean"] for r in records])
    correlations = {
        "obs_norm_vs_advantage": float(np.corrcoef(obs_n, adv)[0, 1]),
        "obs_norm_vs_argmax_dist": float(np.corrcoef(obs_n, amx)[0, 1]),
        "obs_norm_vs_q_sota_mean": float(np.corrcoef(obs_n, q_sota)[0, 1]),
    }

    # ── 4. Time-series visualisation ────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharex=True)
    for sc_idx, scen in enumerate(("load_step_1", "load_step_2")):
        for metric_idx, (metric, label) in enumerate([
            ("advantage", "advantage (a_sota vs random)"),
            ("argmax_dist", "argmax_dist (L2 to a_sota)"),
        ]):
            ax = axes[metric_idx][sc_idx]
            for ag in sorted(by_agent):
                xs, ys = [], []
                for step in range(50):
                    recs = [r for r in by_step[(scen, step)] if r["agent"] == ag]
                    if recs:
                        xs.append(step)
                        ys.append(np.median([r[metric] for r in recs]))
                ax.plot(xs, ys, marker=".", lw=1, label=f"ag{ag}")
            if metric == "advantage":
                ax.axhline(0.0, color="red", lw=0.7, ls="--")
            else:
                ax.axhline(ARGMAX_DIST_FAIL, color="red", lw=0.7, ls="--",
                          label=f"50% diag={ARGMAX_DIST_FAIL:.2f}")
            ax.axvspan(0, 5, alpha=0.07, color="orange")    # impulse
            ax.axvspan(5, 15, alpha=0.07, color="yellow")    # rising
            ax.axvspan(15, 30, alpha=0.07, color="green")    # decaying
            ax.axvspan(30, 50, alpha=0.07, color="blue")     # settling
            ax.set_title(f"{scen}: {label}")
            ax.set_xlabel("step")
            ax.legend(fontsize=7, loc="best")
    fig.suptitle("R87-W1 phase-resolved on-manifold critic forensics")
    fig.tight_layout()
    fig.savefig(OUT / "advantage_timeseries.png", dpi=110)
    plt.close(fig)

    summary = {
        "round": "R87",
        "wave": "W1_phase_resolved",
        "source_cache": str(CACHE.relative_to(ROOT)),
        "n_records": len(records),
        "thresholds": {
            "advantage_fail": ADVANTAGE_FAIL,
            "argmax_dist_fail_rel_diag": ARGMAX_DIST_FAIL_FRACTION,
            "argmax_dist_fail_abs": ARGMAX_DIST_FAIL,
            "action_diagonal": ACTION_DIAGONAL,
        },
        "per_phase_global": per_phase_global,
        "per_agent_global": per_agent_global,
        "phase_pass": phase_pass,
        "gate": gate,
        "correlations": correlations,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    # ── 5. Print human-readable digest ───────────────────────────────────
    print("\n=== R87-W1 phase-resolved digest ===")
    print(f"Gate: {gate}")
    print("\nPer-phase global stats:")
    print(f"{'phase':<10} {'n':>4} {'adv_med':>10} {'adv_pos%':>9} "
          f"{'amx/diag':>10} {'q12':>8} {'PASS':>6}")
    for ph in ("impulse", "rising", "decaying", "settling"):
        s = per_phase_global[ph]
        print(f"{ph:<10} {s['n']:>4} {s['advantage_median']:>+10.5f} "
              f"{s['advantage_pos_frac']*100:>8.1f}% "
              f"{s['argmax_dist_rel_diag_median']:>10.3f} "
              f"{s['q1q2_disagreement_median']:>8.4f} "
              f"{'YES' if phase_pass[ph] else 'NO':>6}")
    print("\nPer-agent global stats:")
    for ag, s in per_agent_global.items():
        print(f"  {ag}: adv_med={s['advantage_median']:+.5f} "
              f"amx/diag={s['argmax_dist_rel_diag_median']:.3f} "
              f"q12={s['q1q2_disagreement_median']:.4f}")
    print("\nObs-norm correlations:")
    for k, v in correlations.items():
        print(f"  {k}: {v:+.4f}")
    print(f"\nWritten: {OUT}/{{summary.json, per_phase_table.csv, advantage_timeseries.png}}")


if __name__ == "__main__":
    main()
