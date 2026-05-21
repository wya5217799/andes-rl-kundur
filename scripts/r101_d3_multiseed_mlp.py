"""R101-W1: Multi-seed MLP D3 redo on R72_w4 SOTA — closes CLM-0168 retraction.

CLM-0168 argued the R91 finding ([[CLM-0163]] R²=−0.41 at γ=0.99) was an
MLP regression-noise artifact: a single torch RNG init drew a bad MLP
fit that pulled the cross-agent median negative. R96-W1 same-ckpt re-run
got R²=+0.659 instead. To make the retraction rigorous, this script
runs the identical rollout once, then fits **10 MLP seeds** against the
same (obs, return) data, reports R² distribution (mean ± std) per
(γ, agent).

If the R²(γ=0.99) distribution spans [-0.4, +0.7] across MLP seeds, the
fit is too unstable to draw any conclusion — both CLM-0163 and the R96
"+0.66" reading are inside the noise floor.

If it converges to a tight band > 0 → CLM-0163 was a true outlier;
CLM-0168 retraction stands and the on-manifold story is "obs IS
predictive of return at all γ".

Zero ANDES dependence after the initial rollout (data is cached for
the seed loop). Wall: ~30s ANDES + 10 × 4γ × 4agent × ~3s fit ≈ ~10 min.

Output: results/r101_d3_multiseed_mlp/summary.json + per_seed.csv

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r101_d3_multiseed_mlp.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

# ─── Config ───────────────────────────────────────────────────────────
SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r101_d3_multiseed_mlp"
ENV_SEED = 42
STEPS = 50
GAMMAS = [0.0, 0.9, 0.99, 1.0]
TRAIN_FRAC = 0.8
MLP_HIDDEN = 64
MLP_EPOCHS = 300
MLP_LR = 1e-3
MLP_DROPOUT = 0.10
N_MLP_SEEDS = 10
DEVICE = torch.device("cpu")


# ─── Rollout capture (same as R91/R96) ────────────────────────────────

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


# ─── MLP regressor ────────────────────────────────────────────────────

class MLP(nn.Module):
    def __init__(self, in_dim: int, out_dim: int, hidden: int = MLP_HIDDEN) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Dropout(MLP_DROPOUT),
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Dropout(MLP_DROPOUT),
            nn.Linear(hidden, out_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2))
    if ss_tot <= 1e-12:
        return 1.0 if ss_res < 1e-12 else 0.0
    return 1.0 - ss_res / ss_tot


def fit_mlp(X: np.ndarray, Y: np.ndarray, *, mlp_seed: int, split_seed: int) -> float:
    """Seed both torch (MLP init + dropout + Adam state) and numpy (split). Return test R²."""
    rng = np.random.default_rng(split_seed)
    n = X.shape[0]
    perm = rng.permutation(n)
    n_tr = int(TRAIN_FRAC * n)
    tr, te = perm[:n_tr], perm[n_tr:]

    x_mean = X[tr].mean(axis=0, keepdims=True)
    x_std = X[tr].std(axis=0, keepdims=True) + 1e-6
    y_mean = Y[tr].mean(axis=0, keepdims=True) if Y.ndim > 1 else Y[tr].mean()
    y_std = Y[tr].std(axis=0, keepdims=True) + 1e-6 if Y.ndim > 1 else Y[tr].std() + 1e-6

    Xn = (X - x_mean) / x_std
    Yn = (Y - y_mean) / y_std

    Xt_tr = torch.from_numpy(Xn[tr].astype(np.float32))
    Yt_tr = torch.from_numpy(Yn[tr].astype(np.float32))
    Xt_te = torch.from_numpy(Xn[te].astype(np.float32))

    if Y.ndim == 1:
        Yt_tr = Yt_tr.unsqueeze(-1)
        out_dim = 1
    else:
        out_dim = Y.shape[1]

    torch.manual_seed(mlp_seed)
    model = MLP(X.shape[1], out_dim).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=MLP_LR)
    loss_fn = nn.MSELoss()
    for _ in range(MLP_EPOCHS):
        model.train()
        opt.zero_grad()
        loss = loss_fn(model(Xt_tr), Yt_tr)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        y_pred_te = model(Xt_te).cpu().numpy() * y_std + y_mean

    if Y.ndim == 1:
        return _r2(Y[te].reshape(-1, 1), y_pred_te)
    return _r2(Y[te], y_pred_te)


# ─── Main ─────────────────────────────────────────────────────────────

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[R101] Load SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"[R101] {len(agents)} agents loaded")

    print("[R101] Capturing rollouts...")
    all_recs: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        t_s = time.time()
        recs = capture_rollout(scen_name, delta_u, agents)
        print(f"  {scen_name}: {len(recs)} records in {time.time()-t_s:.1f}s")
        all_recs.extend(recs)

    if not all_recs:
        print("FATAL: no records")
        return 1

    # Fit 10 MLP seeds × 4 gammas × 4 agents for R1 (return) AND R2 (action)
    print(f"\n[R101] Multi-seed MLP fits: N_seeds={N_MLP_SEEDS}")

    # Result store: results[gamma_key][agent_idx] = list of R² across seeds
    per_gamma_per_agent: dict[str, dict[int, list[float]]] = {f"g{g}": {} for g in GAMMAS}
    per_agent_r2_action: dict[int, list[float]] = {}

    for agent_i in range(4):
        agent_recs = [r for r in all_recs if r["agent"] == agent_i]
        if not agent_recs:
            continue
        X_obs = np.array([r["obs"] for r in agent_recs], dtype=np.float32)
        Y_act = np.array([r["sota_action"] for r in agent_recs], dtype=np.float32)

        # For each γ, pre-compute returns, then fit N_MLP_SEEDS times
        for gamma in GAMMAS:
            returns = compute_returns(agent_recs, gamma)
            Y_ret = np.array(returns, dtype=np.float32)

            r2_list = []
            for s in range(N_MLP_SEEDS):
                mlp_seed = 1000 + s * 17
                split_seed = 2000 + s * 19  # ALSO vary the train/test split
                r2 = fit_mlp(X_obs, Y_ret, mlp_seed=mlp_seed, split_seed=split_seed)
                r2_list.append(r2)
            per_gamma_per_agent[f"g{gamma}"][agent_i] = r2_list

        # R2 obs→action (single per agent)
        r2_act_list = []
        for s in range(N_MLP_SEEDS):
            mlp_seed = 1000 + s * 17
            split_seed = 2000 + s * 19
            r2 = fit_mlp(X_obs, Y_act, mlp_seed=mlp_seed, split_seed=split_seed)
            r2_act_list.append(r2)
        per_agent_r2_action[agent_i] = r2_act_list
        print(f"  agent {agent_i}: γ=0.99 R² range [{min(per_gamma_per_agent['g0.99'][agent_i]):+.3f}, "
              f"{max(per_gamma_per_agent['g0.99'][agent_i]):+.3f}] across {N_MLP_SEEDS} seeds")

    # Per-gamma summary across 4 agents × 10 seeds = 40 fits
    summary_per_gamma: dict[str, dict] = {}
    for gamma in GAMMAS:
        gk = f"g{gamma}"
        all_r2 = []
        for ai in range(4):
            all_r2.extend(per_gamma_per_agent[gk].get(ai, []))
        if not all_r2:
            continue
        arr = np.array(all_r2)
        summary_per_gamma[gk] = {
            "n_fits": int(len(arr)),
            "mean":   float(arr.mean()),
            "std":    float(arr.std()),
            "p10":    float(np.percentile(arr, 10)),
            "p50":    float(np.percentile(arr, 50)),
            "p90":    float(np.percentile(arr, 90)),
            "min":    float(arr.min()),
            "max":    float(arr.max()),
            "frac_negative": float((arr < 0).mean()),
            "per_agent_r2_lists": {str(k): v for k, v in per_gamma_per_agent[gk].items()},
        }

    # R2 action summary
    all_r2_act = []
    for ai in range(4):
        all_r2_act.extend(per_agent_r2_action.get(ai, []))
    arr_act = np.array(all_r2_act)
    summary_action = {
        "n_fits": int(len(arr_act)),
        "mean": float(arr_act.mean()),
        "std":  float(arr_act.std()),
        "p10":  float(np.percentile(arr_act, 10)),
        "p50":  float(np.percentile(arr_act, 50)),
        "p90":  float(np.percentile(arr_act, 90)),
        "min":  float(arr_act.min()),
        "max":  float(arr_act.max()),
        "per_agent_r2_lists": {str(k): v for k, v in per_agent_r2_action.items()},
    }

    # Verdict
    g099_mean = summary_per_gamma["g0.99"]["mean"]
    g099_std = summary_per_gamma["g0.99"]["std"]
    g099_frac_neg = summary_per_gamma["g0.99"]["frac_negative"]
    g099_min = summary_per_gamma["g0.99"]["min"]
    g099_max = summary_per_gamma["g0.99"]["max"]

    if g099_mean > 0.3 and g099_frac_neg < 0.10:
        gate = "RETRACTION_STANDS_OBS_PREDICTIVE"
        interp = (
            f"γ=0.99 R² distribution mean={g099_mean:+.3f} std={g099_std:.3f}, "
            f"only {g099_frac_neg:.0%} of fits negative. CLM-0163's R²=−0.41 was an "
            f"outlier on the long-left tail (min={g099_min:+.3f}). True signal: obs IS "
            f"moderately predictive of paper-γ return. CLM-0168 retraction stands; "
            f"the value-horizon mismatch hypothesis is empirically dead."
        )
    elif g099_mean > 0 and g099_frac_neg < 0.40:
        gate = "RETRACTION_STANDS_OBS_PARTIALLY_PREDICTIVE"
        interp = (
            f"γ=0.99 R² mean={g099_mean:+.3f} std={g099_std:.3f} — positive but with "
            f"{g099_frac_neg:.0%} fits negative. Effect is real but MLP is unstable. "
            f"Use ridge or more samples before drawing R85+ conclusions."
        )
    elif g099_mean < 0:
        gate = "CLM_0163_REINSTATED"
        interp = (
            f"γ=0.99 R² mean is NEGATIVE ({g099_mean:+.3f}). CLM-0163's value-horizon "
            f"mismatch hypothesis is supported by the multi-seed distribution. "
            f"CLM-0168 retraction may need re-retraction."
        )
    else:
        gate = "UNINFORMATIVE_NOISE_FLOOR"
        interp = (
            f"γ=0.99 R² range [{g099_min:+.3f}, {g099_max:+.3f}] crosses 0 with "
            f"large variance. MLP fit is too noisy on N_train=80; finding requires "
            f"larger samples or a stable regressor."
        )

    summary = {
        "round": "R101",
        "wave": "W1_multiseed_MLP_redo",
        "title": "Multi-seed MLP D3 redo on R72_w4 — closes CLM-0168 retraction",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "suffix": "best",
        "n_records": len(all_recs),
        "n_mlp_seeds": N_MLP_SEEDS,
        "gammas": GAMMAS,
        "per_gamma": summary_per_gamma,
        "obs2action": summary_action,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
            "g099_mean": g099_mean,
            "g099_std": g099_std,
            "g099_frac_negative": g099_frac_neg,
            "g099_range": [g099_min, g099_max],
        },
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n[R101] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}")
    print()
    print(f"  Per-γ R² distribution ({N_MLP_SEEDS} MLP seeds × 4 agents = 40 fits):")
    for gamma in GAMMAS:
        s = summary_per_gamma[f"g{gamma}"]
        print(f"    γ={gamma:<5}: mean={s['mean']:+.3f} ± {s['std']:.3f}  "
              f"[{s['min']:+.3f}, {s['max']:+.3f}]  frac_neg={s['frac_negative']:.2f}")
    print()
    s_act = summary_action
    print(f"  R2 obs→action: mean={s_act['mean']:+.3f} ± {s_act['std']:.3f}  "
          f"[{s_act['min']:+.3f}, {s_act['max']:+.3f}]")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
