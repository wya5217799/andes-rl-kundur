"""R97-W1 — Cross-ckpt action-coordination diagnostic (CLM-0170 universalisation).

For each of N=6 SOTA ckpts (R58 SAC + 5× TD3-LSTM), runs ANDES rollout
2 scenarios × 50 steps × 4 agents, records sota_action per step,
applies R92-W1 axes (effort / corr / saturation / specialisation /
consistency), aggregates cross-ckpt pass/fail counts.

Mirrors R84-d2b rollout protocol (no critic Q probes — only need actions).

Output: results/r97_cross_ckpt_action_coord/{<ckpt_id>/per_step.json,
        <ckpt_id>/summary.json, cross_ckpt_aggregate.json, heatmap.png}

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r97_w1_cross_ckpt_action_coord.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402


# ─── Config ───────────────────────────────────────────────────────────
OUT_DIR = ROOT / "results" / "r97_cross_ckpt_action_coord"
ENV_SEED = 42
STEPS = 50
ACTION_DIM = 2
DEVICE = torch.device("cpu")
SATURATION_THRESHOLD = 0.95
N_AGENTS = 4

# Candidate ckpts (V4 obs_dim=7 paper-faithful)
CKPTS = [
    ("C1_R72_w4_TD3LSTM_s54",  "r72_w4_lstm_tau001_warmup5_s54"),
    ("C2_R68_w2_TD3LSTM_s51",  "r68_w2_lstm_tau001_s51"),
    ("C3_R69_w3_TD3LSTM_s50",  "r69_w3_lstm_tau001_warmup20_s50"),
    ("C4_R73_w3_TD3LSTM_s54",  "r73_w3_lstm_tau001_warmup20_s54"),
    ("C5_R75_w2_TD3LSTM_s59",  "r75_w2_lstm_tau001_warmup20_s59"),
    ("C6_R58_SAC_s49",          "r58_paper_strict_pure_radsec_sac_s49"),
]
SCENARIO_NAMES = list(SCENARIOS.keys())


# ─── Per-ckpt rollout (action capture only, no critic probe) ─────────

def rollout_one_ckpt(ckpt_dir: Path) -> list[dict]:
    """Returns 400 records (2 scen × 50 step × 4 agents) of sota_action."""
    agents = load_agents(ckpt_dir, suffix="best")
    if len(agents) != N_AGENTS:
        raise ValueError(f"Expected {N_AGENTS} agents, got {len(agents)}")

    all_records: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
        try:
            env.seed(ENV_SEED)
            env.STEPS_PER_EPISODE = STEPS
            obs = env.reset(delta_u=delta_u)
            h_actor = [ag.actor.init_hidden(1, DEVICE) for ag in agents]

            for step in range(STEPS):
                actions: dict[int, np.ndarray] = {}
                for i, ag in enumerate(agents):
                    obs_t = torch.as_tensor(
                        obs[i], dtype=torch.float32, device=DEVICE
                    ).unsqueeze(0)
                    with torch.no_grad():
                        sota_action_t, h_actor_new = ag.actor(obs_t, h_actor[i])
                    h_actor[i] = h_actor_new
                    a_np = sota_action_t.cpu().numpy().flatten().astype(np.float32)
                    actions[i] = a_np
                    all_records.append({
                        "scenario": scen_name,
                        "step": step,
                        "agent": i,
                        "sota_action": a_np.tolist(),
                    })

                obs, _r, done, info = env.step(actions)
                if info.get("tds_failed"):
                    print(f"    [tds_failed @ step {step}]")
                    break
                if done:
                    break
        finally:
            env.close()
    return all_records


# ─── R92-W1 axes (lifted from scripts/r92_w1_action_coord.py) ────────

def load_action_tensor(records: list[dict]) -> np.ndarray:
    arr = np.full((len(SCENARIO_NAMES), N_AGENTS, STEPS, 2), np.nan, dtype=float)
    for r in records:
        si = SCENARIO_NAMES.index(r["scenario"])
        arr[si, r["agent"], r["step"], :] = r["sota_action"]
    return arr


def per_ckpt_axes(records: list[dict]) -> dict:
    actions = load_action_tensor(records)  # (2, 4, 50, 2)

    # Effort
    effort_rows = []
    for si, scen in enumerate(SCENARIO_NAMES):
        l2_per_agent = np.linalg.norm(actions[si], axis=-1).mean(axis=-1)
        total_effort = l2_per_agent.sum()
        for ag in range(N_AGENTS):
            seq = actions[si, ag]
            effort_rows.append({
                "scenario": scen, "agent": ag,
                "mean_L2": float(np.linalg.norm(seq, axis=-1).mean()),
                "effort_share": float(l2_per_agent[ag] / total_effort),
            })

    # Correlation: 4×4 per (scen, comp)
    corr_matrices = {}
    max_abs_off = 0.0
    high_corr_pairs = []
    kundur_signature_dM_LS1 = False  # ag0-ag1 r > 0.8 AND ag0-ag2 r < -0.8
    for si, scen in enumerate(SCENARIO_NAMES):
        for comp_idx, comp_name in enumerate(("dM_norm", "dD_norm")):
            mat = np.corrcoef(actions[si, :, :, comp_idx])
            # Handle NaN (constant action sequences)
            mat = np.nan_to_num(mat, nan=0.0)
            corr_matrices[f"{scen}_{comp_name}"] = mat.round(4).tolist()
            for i in range(N_AGENTS):
                for j in range(i + 1, N_AGENTS):
                    rij = mat[i, j]
                    if abs(rij) > 0.8:
                        high_corr_pairs.append({
                            "scenario": scen, "comp": comp_name,
                            "i": i, "j": j, "r": float(rij),
                        })
                    max_abs_off = max(max_abs_off, abs(rij))
            # Kundur 2-area signature (LS1 ΔM only)
            if si == 0 and comp_idx == 0:
                r01 = mat[0, 1]
                r02 = mat[0, 2]
                if r01 > 0.8 and r02 < -0.8:
                    kundur_signature_dM_LS1 = True

    # Saturation: per (scen, agent, comp)
    sat_rows = []
    max_sat = 0.0
    for si, scen in enumerate(SCENARIO_NAMES):
        for ag in range(N_AGENTS):
            for comp_idx, comp_name in enumerate(("dM_norm", "dD_norm")):
                seq = actions[si, ag, :, comp_idx]
                sat = float((np.abs(seq) > SATURATION_THRESHOLD).mean())
                max_sat = max(max_sat, sat)
                sat_rows.append({
                    "scenario": scen, "agent": ag, "comp": comp_name,
                    "sat_fraction": sat,
                })

    # ΔD lockstep check (any ΔD pair |r| ≥ 0.9 across 4 agents)
    dD_lockstep = any(
        p["comp"] == "dD_norm" and abs(p["r"]) >= 0.9 for p in high_corr_pairs
    )

    return {
        "effort_rows": effort_rows,
        "corr_matrices": corr_matrices,
        "max_abs_off_diagonal": float(max_abs_off),
        "high_corr_pairs": high_corr_pairs,
        "kundur_signature_dM_LS1": bool(kundur_signature_dM_LS1),
        "sat_rows": sat_rows,
        "max_saturation_fraction": float(max_sat),
        "dD_lockstep_high": bool(dD_lockstep),
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    per_ckpt_results = []
    for ckpt_id, ckpt_subdir in CKPTS:
        ckpt_dir = ROOT / "results" / ckpt_subdir
        if not ckpt_dir.exists():
            print(f"[R97-W1] SKIP {ckpt_id}: dir missing {ckpt_dir}")
            continue
        print(f"\n[R97-W1] === {ckpt_id} ({ckpt_subdir}) ===")
        t_ckpt = time.time()
        records = rollout_one_ckpt(ckpt_dir)
        axes = per_ckpt_axes(records)

        # save per-ckpt data
        ckpt_out = OUT_DIR / ckpt_id
        ckpt_out.mkdir(parents=True, exist_ok=True)
        (ckpt_out / "per_step.json").write_text(json.dumps(records))
        (ckpt_out / "summary.json").write_text(json.dumps(axes, indent=2))

        per_ckpt_results.append({
            "ckpt_id": ckpt_id,
            "ckpt_dir": ckpt_subdir,
            "max_saturation_fraction": axes["max_saturation_fraction"],
            "max_abs_off_diagonal": axes["max_abs_off_diagonal"],
            "dD_lockstep_high": axes["dD_lockstep_high"],
            "kundur_signature_dM_LS1": axes["kundur_signature_dM_LS1"],
            "high_corr_pair_count": len(axes["high_corr_pairs"]),
        })
        print(f"    saturation_max={axes['max_saturation_fraction']:.3f} "
              f"max|corr|={axes['max_abs_off_diagonal']:.3f} "
              f"dD_lockstep={axes['dD_lockstep_high']} "
              f"Kundur_sig={axes['kundur_signature_dM_LS1']} "
              f"({time.time()-t_ckpt:.1f}s)")

    # Cross-ckpt aggregate
    n = len(per_ckpt_results)
    n_sat_high = sum(1 for r in per_ckpt_results if r["max_saturation_fraction"] >= 0.50)
    n_lockstep_dD = sum(1 for r in per_ckpt_results if r["dD_lockstep_high"])
    n_kundur_sig = sum(1 for r in per_ckpt_results if r["kundur_signature_dM_LS1"])
    median_sat = float(np.median([r["max_saturation_fraction"] for r in per_ckpt_results])) if n else 0.0
    median_corr = float(np.median([r["max_abs_off_diagonal"] for r in per_ckpt_results])) if n else 0.0

    aggregate = {
        "round": "R97",
        "wave": "W1_cross_ckpt_action_coord",
        "n_ckpts": n,
        "thresholds": {
            "saturation_per_ckpt": 0.50,
            "saturation_universalisation": "5 of 6",
            "dD_lockstep_per_ckpt": 0.90,
            "lockstep_universalisation": "4 of 6",
            "kundur_sig_universalisation": "4 of 6",
        },
        "per_ckpt": per_ckpt_results,
        "aggregate": {
            "n_ckpts_saturation_high": n_sat_high,
            "n_ckpts_lockstep_dD": n_lockstep_dD,
            "n_ckpts_kundur_sig_dM_LS1": n_kundur_sig,
            "median_saturation_across_ckpts": median_sat,
            "median_off_diag_corr_across_ckpts": median_corr,
        },
        "gate": (
            "UNIVERSALISED"
            if (n_sat_high >= 5 and n_lockstep_dD >= 4)
            else "PARTIAL" if (n_sat_high >= 3 or n_lockstep_dD >= 3) else "FAIL"
        ),
        "wall_s": time.time() - t_start,
    }
    (OUT_DIR / "cross_ckpt_aggregate.json").write_text(json.dumps(aggregate, indent=2))

    # Print digest
    print(f"\n=== R97-W1 cross-ckpt action-coordination digest ===")
    print(f"N ckpts: {n}")
    print(f"Gate: {aggregate['gate']}")
    print(f"")
    print(f"{'ckpt_id':<28s} {'sat_max':>8s} {'max|r|':>8s} {'dD_lockstep':>12s} {'Kundur_sig':>11s}")
    for r in per_ckpt_results:
        print(f"{r['ckpt_id']:<28s} {r['max_saturation_fraction']:>8.3f} "
              f"{r['max_abs_off_diagonal']:>8.3f} {str(r['dD_lockstep_high']):>12s} "
              f"{str(r['kundur_signature_dM_LS1']):>11s}")
    agg = aggregate['aggregate']
    print(f"\nAggregate:")
    print(f"  saturation high (≥0.50): {agg['n_ckpts_saturation_high']}/{n}")
    print(f"  ΔD lockstep (≥0.9):      {agg['n_ckpts_lockstep_dD']}/{n}")
    print(f"  Kundur 2-area sig:       {agg['n_ckpts_kundur_sig_dM_LS1']}/{n}")
    print(f"  median sat across ckpts: {agg['median_saturation_across_ckpts']:.3f}")
    print(f"  median |off-diag| corr:  {agg['median_off_diag_corr_across_ckpts']:.3f}")
    print(f"\nWritten to: {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
