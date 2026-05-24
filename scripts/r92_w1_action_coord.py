"""R92-W1 — multi-agent action-coordination diagnostic on cached SOTA rollout.

Reads `results/r84_d2b_q_landscape_trajectory/per_step.json` (400 records,
4 agents × 2 scen × 50 steps; each carries `sota_action[0] = ΔM_norm`,
`sota_action[1] = ΔD_norm`).

Six analyses (see plan.md):
A. Per-agent action effort distribution
B. Inter-agent action correlation matrices
C. Time-series visualisation (4 panels)
D. ΔM-vs-ΔD specialisation per agent
E. Action saturation frequency
F. Cross-scenario role consistency

Output: results/r92_w1_action_coord/{summary.json, action_timeseries.png,
corr_matrices.png, per_agent_table.csv}.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "results" / "r84_d2b_q_landscape_trajectory" / "per_step.json"
OUT = ROOT / "results" / "r92_w1_action_coord"
OUT.mkdir(parents=True, exist_ok=True)

N_AGENTS = 4
N_STEPS = 50
SCENARIOS = ("load_step_1", "load_step_2")
ACTION_COMPONENT_NAMES = ("dM_norm", "dD_norm")
SATURATION_THRESHOLD = 0.95          # |a| > 0.95 counts as saturated


def load_action_tensor(records: list[dict]) -> np.ndarray:
    """Return (n_scen, n_agents, n_steps, 2) array."""
    arr = np.full((len(SCENARIOS), N_AGENTS, N_STEPS, 2), np.nan, dtype=float)
    for r in records:
        si = SCENARIOS.index(r["scenario"])
        arr[si, r["agent"], r["step"], :] = r["sota_action"]
    if np.isnan(arr).any():
        missing = int(np.isnan(arr).any(axis=-1).sum())
        print(f"WARN: {missing} (scen, agent, step) cells are missing")
    return arr


# ───────────────────────────────────────────────────────────────────────
# Axis A. Effort distribution
# ───────────────────────────────────────────────────────────────────────

def axis_a_effort(actions: np.ndarray) -> dict:
    """Per (scenario, agent): mean / std / max of |ΔM|, |ΔD|, L2."""
    rows = []
    for si, scen in enumerate(SCENARIOS):
        l2_per_agent = np.linalg.norm(actions[si], axis=-1).mean(axis=-1)  # (n_agents,)
        total_effort = l2_per_agent.sum()
        for ag in range(N_AGENTS):
            seq = actions[si, ag]                 # (n_steps, 2)
            abs_dm = np.abs(seq[:, 0])
            abs_dd = np.abs(seq[:, 1])
            l2 = np.linalg.norm(seq, axis=-1)
            rows.append({
                "scenario": scen,
                "agent": ag,
                "mean_abs_dM": float(abs_dm.mean()),
                "max_abs_dM": float(abs_dm.max()),
                "mean_abs_dD": float(abs_dd.mean()),
                "max_abs_dD": float(abs_dd.max()),
                "mean_L2": float(l2.mean()),
                "max_L2": float(l2.max()),
                "effort_share": float(l2_per_agent[ag] / total_effort),
            })
    max_share = max(r["effort_share"] for r in rows)
    return {
        "per_scenario_agent": rows,
        "max_effort_share": float(max_share),
        "structural_flag": bool(max_share >= 0.50),
    }


# ───────────────────────────────────────────────────────────────────────
# Axis B. Inter-agent correlation
# ───────────────────────────────────────────────────────────────────────

def axis_b_correlation(actions: np.ndarray) -> dict:
    """4×4 Pearson corr matrix per (scenario, action_component)."""
    out: dict[str, list[list[float]]] = {}
    max_abs_off = 0.0
    flagged: list[str] = []
    for si, scen in enumerate(SCENARIOS):
        for comp in (0, 1):
            mat = np.corrcoef(actions[si, :, :, comp])   # (4, 4)
            label = f"{scen}_{ACTION_COMPONENT_NAMES[comp]}"
            out[label] = mat.round(4).tolist()
            for i in range(N_AGENTS):
                for j in range(i+1, N_AGENTS):
                    if abs(mat[i, j]) > 0.8:
                        flagged.append(
                            f"{label} agent{i}-agent{j} r={mat[i,j]:+.3f}"
                        )
                    max_abs_off = max(max_abs_off, abs(mat[i, j]))
    return {
        "matrices": out,
        "max_abs_off_diagonal": float(max_abs_off),
        "flagged_high_corr_pairs": flagged,
        "structural_flag": bool(max_abs_off > 0.8),
    }


# ───────────────────────────────────────────────────────────────────────
# Axis D. ΔM vs ΔD specialisation
# ───────────────────────────────────────────────────────────────────────

def axis_d_specialisation(actions: np.ndarray) -> dict:
    """Per (scenario, agent): total |ΔM| / (total |ΔM| + total |ΔD|)."""
    rows = []
    for si, scen in enumerate(SCENARIOS):
        for ag in range(N_AGENTS):
            seq = actions[si, ag]
            sum_abs_dm = float(np.abs(seq[:, 0]).sum())
            sum_abs_dd = float(np.abs(seq[:, 1]).sum())
            ratio = sum_abs_dm / max(sum_abs_dm + sum_abs_dd, 1e-9)
            rows.append({
                "scenario": scen, "agent": ag,
                "sum_abs_dM": sum_abs_dm,
                "sum_abs_dD": sum_abs_dd,
                "dM_share": ratio,
            })
    return {"per_scenario_agent": rows}


# ───────────────────────────────────────────────────────────────────────
# Axis E. Saturation frequency
# ───────────────────────────────────────────────────────────────────────

def axis_e_saturation(actions: np.ndarray) -> dict:
    rows = []
    max_sat = 0.0
    for si, scen in enumerate(SCENARIOS):
        for ag in range(N_AGENTS):
            for comp in (0, 1):
                seq = actions[si, ag, :, comp]
                sat = float((np.abs(seq) > SATURATION_THRESHOLD).mean())
                max_sat = max(max_sat, sat)
                rows.append({
                    "scenario": scen,
                    "agent": ag,
                    "component": ACTION_COMPONENT_NAMES[comp],
                    "sat_fraction": sat,
                })
    return {
        "per_scenario_agent_comp": rows,
        "max_saturation_fraction": float(max_sat),
        "structural_flag": bool(max_sat > 0.30),
    }


# ───────────────────────────────────────────────────────────────────────
# Axis F. Cross-scenario role consistency
# ───────────────────────────────────────────────────────────────────────

def axis_f_consistency(effort_rows: list[dict], spec_rows: list[dict]) -> dict:
    """Compare (effort_share, dM_share) ranks across LS1 vs LS2 per agent."""
    by_scen = {
        s: {r["agent"]: r for r in effort_rows if r["scenario"] == s}
        for s in SCENARIOS
    }
    spec_by_scen = {
        s: {r["agent"]: r for r in spec_rows if r["scenario"] == s}
        for s in SCENARIOS
    }
    per_agent_delta = []
    for ag in range(N_AGENTS):
        eff_diff = abs(by_scen[SCENARIOS[0]][ag]["effort_share"] -
                       by_scen[SCENARIOS[1]][ag]["effort_share"])
        spec_diff = abs(spec_by_scen[SCENARIOS[0]][ag]["dM_share"] -
                        spec_by_scen[SCENARIOS[1]][ag]["dM_share"])
        per_agent_delta.append({
            "agent": ag,
            "effort_share_delta": eff_diff,
            "dM_share_delta": spec_diff,
        })
    max_eff_delta = max(d["effort_share_delta"] for d in per_agent_delta)
    max_spec_delta = max(d["dM_share_delta"] for d in per_agent_delta)
    return {
        "per_agent_deltas": per_agent_delta,
        "max_effort_share_delta": float(max_eff_delta),
        "max_dM_share_delta": float(max_spec_delta),
        "structural_flag": bool(max_eff_delta > 0.20 or max_spec_delta > 0.50),
    }


# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

def main() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not CACHE.exists():
        sys.exit(f"FATAL: cached per_step.json missing at {CACHE}")
    records = json.loads(CACHE.read_text())
    actions = load_action_tensor(records)        # (2, 4, 50, 2)

    a_out = axis_a_effort(actions)
    b_out = axis_b_correlation(actions)
    d_out = axis_d_specialisation(actions)
    e_out = axis_e_saturation(actions)
    f_out = axis_f_consistency(
        a_out["per_scenario_agent"], d_out["per_scenario_agent"]
    )

    # ── Gate ──────────────────────────────────────────────────────────
    flags = [a_out["structural_flag"], b_out["structural_flag"],
              e_out["structural_flag"], f_out["structural_flag"]]
    gate = "STRUCTURAL" if any(flags) else "BALANCED"
    triggered = []
    if a_out["structural_flag"]:
        triggered.append(f"effort_share max={a_out['max_effort_share']:.2f} ≥ 0.50")
    if b_out["structural_flag"]:
        triggered.append(f"max |corr|={b_out['max_abs_off_diagonal']:.2f} > 0.80")
    if e_out["structural_flag"]:
        triggered.append(f"max saturation={e_out['max_saturation_fraction']:.2f} > 0.30")
    if f_out["structural_flag"]:
        triggered.append(
            f"max effort_delta={f_out['max_effort_share_delta']:.2f}, "
            f"max dM_share_delta={f_out['max_dM_share_delta']:.2f}"
        )

    # ── CSV table ─────────────────────────────────────────────────────
    per_agent_combined = []
    for r_eff in a_out["per_scenario_agent"]:
        match = next(d for d in d_out["per_scenario_agent"]
                       if d["scenario"] == r_eff["scenario"]
                       and d["agent"] == r_eff["agent"])
        per_agent_combined.append({
            "scenario": r_eff["scenario"],
            "agent": r_eff["agent"],
            "mean_L2": round(r_eff["mean_L2"], 4),
            "effort_share": round(r_eff["effort_share"], 4),
            "mean_abs_dM": round(r_eff["mean_abs_dM"], 4),
            "mean_abs_dD": round(r_eff["mean_abs_dD"], 4),
            "dM_share": round(match["dM_share"], 4),
        })
    with open(OUT / "per_agent_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(per_agent_combined[0].keys()))
        w.writeheader()
        w.writerows(per_agent_combined)

    # ── Figure 1: time-series of actions ──────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(12, 6), sharex=True)
    for si, scen in enumerate(SCENARIOS):
        for comp in (0, 1):
            ax = axes[comp][si]
            for ag in range(N_AGENTS):
                ax.plot(np.arange(N_STEPS), actions[si, ag, :, comp],
                        lw=1.2, label=f"ag{ag}")
            ax.axhline(0.0, color="black", lw=0.5)
            ax.axhline(+SATURATION_THRESHOLD, color="red", lw=0.5, ls="--", alpha=0.5)
            ax.axhline(-SATURATION_THRESHOLD, color="red", lw=0.5, ls="--", alpha=0.5)
            ax.set_title(f"{scen}: {ACTION_COMPONENT_NAMES[comp]}")
            ax.set_xlabel("step")
            ax.set_ylabel("action (normalized)")
            ax.legend(fontsize=7)
    fig.suptitle("R92-W1 per-agent action trajectories")
    fig.tight_layout()
    fig.savefig(OUT / "action_timeseries.png", dpi=110)
    plt.close(fig)

    # ── Figure 2: correlation matrices ────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(8, 7))
    keys = [f"{s}_{c}" for s in SCENARIOS for c in ACTION_COMPONENT_NAMES]
    for k, (key, ax) in enumerate(zip(keys, axes.flatten())):
        mat = np.array(b_out["matrices"][key])
        ax.imshow(mat, cmap="RdBu_r", vmin=-1, vmax=1)
        for i in range(N_AGENTS):
            for j in range(N_AGENTS):
                ax.text(j, i, f"{mat[i,j]:+.2f}", ha="center", va="center",
                        color="white" if abs(mat[i,j]) > 0.6 else "black",
                        fontsize=8)
        ax.set_title(key)
        ax.set_xticks(range(N_AGENTS))
        ax.set_yticks(range(N_AGENTS))
        ax.set_xticklabels([f"ag{i}" for i in range(N_AGENTS)])
        ax.set_yticklabels([f"ag{i}" for i in range(N_AGENTS)])
    fig.suptitle("R92-W1 inter-agent action correlation")
    fig.tight_layout()
    fig.savefig(OUT / "corr_matrices.png", dpi=110)
    plt.close(fig)

    summary = {
        "round": "R92",
        "wave": "W1_action_coord",
        "source_cache": str(CACHE.relative_to(ROOT)),
        "thresholds": {
            "effort_share_structural": 0.50,
            "corr_structural": 0.80,
            "saturation_structural": 0.30,
            "consistency_effort_delta_structural": 0.20,
            "consistency_dM_share_delta_structural": 0.50,
            "saturation_abs_threshold": SATURATION_THRESHOLD,
        },
        "axis_a_effort": a_out,
        "axis_b_correlation": b_out,
        "axis_d_specialisation": d_out,
        "axis_e_saturation": e_out,
        "axis_f_consistency": f_out,
        "gate": gate,
        "triggered_flags": triggered,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))

    # ── Digest ────────────────────────────────────────────────────────
    print("\n=== R92-W1 action-coordination digest ===")
    print(f"Gate: {gate}")
    if triggered:
        print("Triggered flags:")
        for t in triggered:
            print(f"  - {t}")
    print("\nEffort share per (scen, agent):")
    print(f"  {'scen':<12} {'ag':>2} {'mean_L2':>9} {'effort%':>8} "
          f"{'dM_share':>9} {'sat_dM%':>9} {'sat_dD%':>9}")
    sat_by = {(r["scenario"], r["agent"], r["component"]): r["sat_fraction"]
               for r in e_out["per_scenario_agent_comp"]}
    for r in per_agent_combined:
        sat_dm = sat_by[(r["scenario"], r["agent"], "dM_norm")] * 100
        sat_dd = sat_by[(r["scenario"], r["agent"], "dD_norm")] * 100
        print(f"  {r['scenario']:<12} {r['agent']:>2} {r['mean_L2']:>9.4f} "
              f"{r['effort_share']*100:>7.1f}% {r['dM_share']:>9.4f} "
              f"{sat_dm:>8.1f}% {sat_dd:>8.1f}%")
    print(f"\nMax |off-diag corr|: {b_out['max_abs_off_diagonal']:.3f}")
    if b_out["flagged_high_corr_pairs"]:
        for p in b_out["flagged_high_corr_pairs"]:
            print(f"  flagged: {p}")
    print("\nCross-scenario consistency:")
    for d in f_out["per_agent_deltas"]:
        print(f"  agent {d['agent']}: Δeffort={d['effort_share_delta']:+.4f}, "
              f"ΔdM_share={d['dM_share_delta']:+.4f}")
    print(f"\nWritten to: {OUT}")


if __name__ == "__main__":
    main()
