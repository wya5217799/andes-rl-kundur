"""R101-W2 (ridge sanity): closed-form linear-model D3 cross-check.

CLM-0169 demonstrated MLP regressor has 5-28% catastrophic fit rate at
N_train=80 on the R72_w4 D3 task. Median R² is meaningful but expensive
(needs 10+ MLP seeds). Ridge regression is closed-form (no init RNG),
deterministic given α (regularisation strength), and orders of magnitude
faster — should be the methodology baseline.

If Ridge R²(γ=0.99) ≈ MLP-median (+0.643), CLM-0169's methodology is
validated. If Ridge gives substantially different number (≥ ±0.20 swing),
the MLP-median itself was unstable and CLM-0169 needs further work.

Workflow:
1. Single deterministic SOTA rollout (LS1+LS2, identical to R91 / R96 /
   R101 — should produce bit-identical records).
2. For each (γ, agent), fit Ridge with α ∈ {0.0, 0.1, 1.0, 10.0, 100.0}
   on 80/20 split (5 split seeds for variance estimate).
3. Compare ridge R² distribution (75 fits per γ) vs MLP-median.

Output: `results/r101_ridge_sanity/{summary.json, ridge_table.csv}`

Wall: ~17s ANDES + <5s ridge fits. 1 brief ANDES slot.

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r101_ridge_sanity.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

# ─── Config ───────────────────────────────────────────────────────────
SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r101_ridge_sanity"
ENV_SEED = 42
STEPS = 50
GAMMAS = [0.0, 0.9, 0.99, 1.0]
TRAIN_FRAC = 0.8
ALPHAS = [0.0, 0.1, 1.0, 10.0, 100.0]
N_SPLIT_SEEDS = 5
DEVICE = "cpu"


# ─── Closed-form ridge ────────────────────────────────────────────────

def ridge_fit_predict(X_tr: np.ndarray, Y_tr: np.ndarray,
                     X_te: np.ndarray, alpha: float) -> np.ndarray:
    """Closed-form Ridge: w = (X'X + αI)^-1 X'y, supports multi-output."""
    # Standardise (use train stats only)
    x_mean = X_tr.mean(axis=0, keepdims=True)
    x_std = X_tr.std(axis=0, keepdims=True) + 1e-6
    Xn_tr = (X_tr - x_mean) / x_std
    Xn_te = (X_te - x_mean) / x_std

    if Y_tr.ndim == 1:
        y_mean = float(Y_tr.mean())
        y_std = float(Y_tr.std() + 1e-6)
        Yn_tr = ((Y_tr - y_mean) / y_std).reshape(-1, 1)
    else:
        y_mean = Y_tr.mean(axis=0, keepdims=True)
        y_std = Y_tr.std(axis=0, keepdims=True) + 1e-6
        Yn_tr = (Y_tr - y_mean) / y_std

    # Augment X with bias column
    Xb_tr = np.concatenate([Xn_tr, np.ones((Xn_tr.shape[0], 1))], axis=1)
    Xb_te = np.concatenate([Xn_te, np.ones((Xn_te.shape[0], 1))], axis=1)
    n_features = Xb_tr.shape[1]

    # Ridge: don't regularise bias column
    eye = np.eye(n_features)
    eye[-1, -1] = 0.0
    W = np.linalg.solve(Xb_tr.T @ Xb_tr + alpha * eye, Xb_tr.T @ Yn_tr)
    Yn_pred_te = Xb_te @ W
    return Yn_pred_te * y_std + y_mean


def r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    if y_true.ndim == 1:
        y_true = y_true.reshape(-1, 1)
    if y_pred.ndim == 1:
        y_pred = y_pred.reshape(-1, 1)
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2))
    if ss_tot <= 1e-12:
        return 1.0 if ss_res < 1e-12 else 0.0
    return 1.0 - ss_res / ss_tot


# ─── Rollout (identical to R91/R96/R101) ──────────────────────────────

def capture_rollout(scen_name: str, delta_u: dict, agents: list) -> list[dict]:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    records: list[dict] = []
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS

        for ag in agents:
            if getattr(ag, "is_recurrent", False):
                ag.begin_episode()

        for step in range(STEPS):
            actions: dict[int, np.ndarray] = {}
            obs_dump = {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
            for i, ag in enumerate(agents):
                a_np = ag.select_action(obs[i], deterministic=True)
                actions[i] = np.asarray(a_np, dtype=np.float32)

            next_obs, rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                break

            if isinstance(rewards, dict):
                rew = {i: float(rewards[i]) for i in range(n_agents)}
            elif isinstance(rewards, (list, tuple, np.ndarray)):
                rew = {i: float(rewards[i]) for i in range(n_agents)}
            else:
                rew = {i: float(rewards) for i in range(n_agents)}

            for i in range(n_agents):
                records.append({
                    "scenario": scen_name,
                    "step": step,
                    "agent": i,
                    "obs": obs_dump[i].tolist(),
                    "sota_action": actions[i].tolist(),
                    "reward": rew[i],
                })
            obs = next_obs
            if done:
                break
    finally:
        env.close()
    return records


def compute_returns(records: list[dict], gamma: float) -> list[float]:
    by_key: dict[tuple, list[dict]] = {}
    for r in records:
        by_key.setdefault((r["scenario"], r["agent"]), []).append(r)
    for k in by_key:
        by_key[k].sort(key=lambda x: x["step"])
    out_lookup: dict[tuple, float] = {}
    for k, seq in by_key.items():
        G = 0.0
        for r in reversed(seq):
            G = r["reward"] + gamma * G
            out_lookup[(r["scenario"], r["agent"], r["step"])] = G
    return [out_lookup[(r["scenario"], r["agent"], r["step"])] for r in records]


# ─── Main ─────────────────────────────────────────────────────────────

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[R101-ridge] Load SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"[R101-ridge] {len(agents)} agents")

    all_recs: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        recs = capture_rollout(scen_name, delta_u, agents)
        all_recs.extend(recs)
    print(f"[R101-ridge] {len(all_recs)} records captured")

    # Per (γ, α, split_seed, agent) ridge fit
    # Output structure: per_gamma[γ][α] = list of R² across (split, agent)
    per_gamma_alpha: dict[str, dict[float, list[float]]] = {f"g{g}": {a: [] for a in ALPHAS} for g in GAMMAS}
    per_gamma_alpha_action: dict[float, list[float]] = {a: [] for a in ALPHAS}

    for agent_i in range(4):
        agent_recs = [r for r in all_recs if r["agent"] == agent_i]
        if not agent_recs:
            continue
        X_obs = np.array([r["obs"] for r in agent_recs], dtype=np.float64)
        Y_act = np.array([r["sota_action"] for r in agent_recs], dtype=np.float64)

        for gamma in GAMMAS:
            returns = compute_returns(agent_recs, gamma)
            Y_ret = np.array(returns, dtype=np.float64)

            for split_seed in range(N_SPLIT_SEEDS):
                rng = np.random.default_rng(3000 + split_seed * 11)
                n = X_obs.shape[0]
                perm = rng.permutation(n)
                n_tr = int(TRAIN_FRAC * n)
                tr, te = perm[:n_tr], perm[n_tr:]

                for alpha in ALPHAS:
                    y_pred = ridge_fit_predict(X_obs[tr], Y_ret[tr], X_obs[te], alpha)
                    r2 = r2_score(Y_ret[te], y_pred.flatten())
                    per_gamma_alpha[f"g{gamma}"][alpha].append(r2)

        # R2 obs→action (multi-output ridge)
        for split_seed in range(N_SPLIT_SEEDS):
            rng = np.random.default_rng(3000 + split_seed * 11)
            n = X_obs.shape[0]
            perm = rng.permutation(n)
            n_tr = int(TRAIN_FRAC * n)
            tr, te = perm[:n_tr], perm[n_tr:]

            for alpha in ALPHAS:
                y_pred = ridge_fit_predict(X_obs[tr], Y_act[tr], X_obs[te], alpha)
                r2 = r2_score(Y_act[te], y_pred)
                per_gamma_alpha_action[alpha].append(r2)

    # Summarise by α, then collapse across α with median over α set as "ridge optimum"
    summary_per_gamma: dict[str, dict] = {}
    for gamma in GAMMAS:
        gk = f"g{gamma}"
        by_alpha_summary = {}
        for alpha in ALPHAS:
            arr = np.array(per_gamma_alpha[gk][alpha])
            by_alpha_summary[str(alpha)] = {
                "n_fits": int(len(arr)),
                "mean": float(arr.mean()),
                "median": float(np.median(arr)),
                "p25": float(np.percentile(arr, 25)),
                "p75": float(np.percentile(arr, 75)),
                "min": float(arr.min()),
                "max": float(arr.max()),
                "frac_negative": float((arr < 0).mean()),
            }
        # Pick best α by median R²
        best_alpha = max(ALPHAS, key=lambda a: by_alpha_summary[str(a)]["median"])
        summary_per_gamma[gk] = {
            "by_alpha": by_alpha_summary,
            "best_alpha": best_alpha,
            "best_alpha_median_r2": by_alpha_summary[str(best_alpha)]["median"],
        }

    action_by_alpha = {}
    for alpha in ALPHAS:
        arr = np.array(per_gamma_alpha_action[alpha])
        action_by_alpha[str(alpha)] = {
            "mean": float(arr.mean()),
            "median": float(np.median(arr)),
            "min": float(arr.min()),
            "max": float(arr.max()),
        }
    best_alpha_act = max(ALPHAS, key=lambda a: action_by_alpha[str(a)]["median"])

    # Cross-check against MLP-median (CLM-0169)
    MLP_MEDIANS = {"g0.0": 0.907, "g0.9": 0.286, "g0.99": 0.643, "g1.0": 0.666}
    consistency: dict[str, dict] = {}
    for gk, ridge_sum in summary_per_gamma.items():
        mlp_med = MLP_MEDIANS.get(gk)
        ridge_med = ridge_sum["best_alpha_median_r2"]
        consistency[gk] = {
            "mlp_median_r2": mlp_med,
            "ridge_best_median_r2": ridge_med,
            "delta": ridge_med - mlp_med if mlp_med is not None else None,
        }

    max_abs_delta = max(abs(c["delta"]) for c in consistency.values() if c["delta"] is not None)
    if max_abs_delta < 0.10:
        gate = "RIDGE_AGREES_CLM_0169_RIGOROUS"
        interp = f"Ridge R² within ±0.10 of MLP-median for all γ (max |Δ|={max_abs_delta:.3f}). CLM-0169 methodology validated."
    elif max_abs_delta < 0.20:
        gate = "RIDGE_BROADLY_AGREES"
        interp = f"Ridge within ±0.20 of MLP-median (max |Δ|={max_abs_delta:.3f}). CLM-0169 directionally correct, some γ-specific drift."
    else:
        gate = "RIDGE_DISAGREES_INVESTIGATE"
        interp = f"Ridge differs from MLP-median by up to {max_abs_delta:.3f}. MLP median may itself be biased. Re-evaluate CLM-0169."

    summary = {
        "round": "R101",
        "wave": "W2_ridge_sanity",
        "title": "Ridge cross-check of R101 MLP-median R² (CLM-0169 validation)",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "alphas": ALPHAS,
        "n_split_seeds": N_SPLIT_SEEDS,
        "per_gamma_ridge": summary_per_gamma,
        "obs2action_ridge": {"by_alpha": action_by_alpha, "best_alpha": best_alpha_act},
        "consistency_with_clm0169": consistency,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
            "max_abs_delta_vs_mlp_median": max_abs_delta,
        },
        "wall_seconds": time.time() - t0,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n[R101-ridge] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}\n")
    print(f"  γ        | MLP median | Ridge best-α median | Δ      | best α")
    for gk in [f"g{g}" for g in GAMMAS]:
        c = consistency[gk]
        rs = summary_per_gamma[gk]
        print(f"  {gk[1:]:<8} | {c['mlp_median_r2']:+.3f}     | {c['ridge_best_median_r2']:+.3f}              | {c['delta']:+.3f} | α={rs['best_alpha']:.2f}")
    print(f"\n  R2 obs→action ridge best (α={best_alpha_act}): median={action_by_alpha[str(best_alpha_act)]['median']:+.3f}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
