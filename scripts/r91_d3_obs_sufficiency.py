"""R91-W1 (D3): Obs sufficiency for V*/π* on R72_w4 SOTA trajectory.

Phase 1: capture one full deterministic SOTA rollout on LS1+LS2 with
  - full obs vector (not just norm)
  - per-step scalar reward (per-agent if multi-agent dict, else broadcast)
  - LSTM h_actor (h, c)
  - action_sota
Phase 2: offline fit 4 MLP regressors on the captured samples:
  R1: obs       → return_γ   (multiple γ ∈ {0.0, 0.9, 0.99, 1.0})
  R2: obs       → action*    (memoryless BC ceiling)
  R3: (obs, h)  → action*    (full-info BC ceiling — uses h_actor)
  R4: obs       → next_obs   (forward-model sufficiency)
Phase 3: report per-regressor test R²; classify obs sufficiency.

Gate (R85+ priority pivot informed by this):
- obs_sufficient = R1 ≥ 0.5 AND R2 ≥ 0.7
- h_essential    = R3 − R2 ≥ 0.3
- dynamics_markov = R4 ≥ 0.5

Output: results/r91_d3_obs_sufficiency/summary.json

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r91_d3_obs_sufficiency.py
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
OUT_DIR = ROOT / "results" / "r91_d3_obs_sufficiency"
ENV_SEED = 42
STEPS = 50
GAMMAS = [0.0, 0.9, 0.99, 1.0]
TRAIN_FRAC = 0.8
MLP_HIDDEN = 64
MLP_EPOCHS = 300
MLP_LR = 1e-3
MLP_DROPOUT = 0.10
DEVICE = torch.device("cpu")
RNG = np.random.default_rng(seed=0xD3)


# ─── Rollout capture ──────────────────────────────────────────────────

def capture_rollout(scen_name: str, delta_u: dict, agents: list) -> list[dict]:
    """One scenario rollout, capture (obs, action, reward, h_actor)."""
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    records: list[dict] = []
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS

        h_actor = [ag.actor.init_hidden(1, DEVICE) for ag in agents]

        for step in range(STEPS):
            actions: dict[int, np.ndarray] = {}
            obs_dump = {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
            h_dump = []
            for i, ag in enumerate(agents):
                obs_t = torch.as_tensor(obs[i], dtype=torch.float32, device=DEVICE).unsqueeze(0)
                with torch.no_grad():
                    a_t, h_new = ag.actor(obs_t, h_actor[i])
                # h_actor is (h, c) tuple of (1, hidden) tensors
                h_dump.append(
                    np.concatenate([
                        h_actor[i][0].cpu().numpy().flatten(),
                        h_actor[i][1].cpu().numpy().flatten(),
                    ]).astype(np.float32)
                )
                h_actor[i] = h_new
                actions[i] = a_t.cpu().numpy().flatten().astype(np.float32)

            next_obs, rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                print(f"  [tds_failed @ step {step}]")
                break

            # Rewards: env may return scalar (shared) or dict per agent
            if isinstance(rewards, dict):
                rew_per_agent = {i: float(rewards[i]) for i in range(n_agents)}
            elif isinstance(rewards, (list, tuple, np.ndarray)):
                rew_per_agent = {i: float(rewards[i]) for i in range(n_agents)}
            else:
                rew_per_agent = {i: float(rewards) for i in range(n_agents)}

            for i in range(n_agents):
                records.append({
                    "scenario": scen_name,
                    "step": step,
                    "agent": i,
                    "obs": obs_dump[i].tolist(),
                    "next_obs": next_obs[i].copy().astype(np.float32).tolist(),
                    "h_actor": h_dump[i].tolist(),
                    "sota_action": actions[i].tolist(),
                    "reward": rew_per_agent[i],
                })

            obs = next_obs
            if done:
                break
    finally:
        env.close()
    return records


# ─── Returns ─────────────────────────────────────────────────────────

def compute_returns(records: list[dict], gamma: float) -> list[float]:
    """Backward γ-discounted sum. Sorted by (scenario, agent, step)."""
    by_key: dict[tuple, list[dict]] = {}
    for r in records:
        by_key.setdefault((r["scenario"], r["agent"]), []).append(r)
    for k in by_key:
        by_key[k].sort(key=lambda x: x["step"])

    returns_lookup: dict[tuple, float] = {}
    for k, seq in by_key.items():
        G = 0.0
        for r in reversed(seq):
            G = r["reward"] + gamma * G
            returns_lookup[(r["scenario"], r["agent"], r["step"])] = G
    return [returns_lookup[(r["scenario"], r["agent"], r["step"])] for r in records]


# ─── Regressors ───────────────────────────────────────────────────────

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


def _r2_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2))
    if ss_tot <= 1e-12:
        return 1.0 if ss_res < 1e-12 else 0.0
    return 1.0 - ss_res / ss_tot


def fit_mlp_regressor(X: np.ndarray, Y: np.ndarray, *, label: str) -> dict:
    """80/20 split, train MLP, return train+test R²."""
    n = X.shape[0]
    perm = RNG.permutation(n)
    n_tr = int(TRAIN_FRAC * n)
    tr, te = perm[:n_tr], perm[n_tr:]

    # Standardise inputs and outputs for stable training
    x_mean = X[tr].mean(axis=0, keepdims=True)
    x_std = X[tr].std(axis=0, keepdims=True) + 1e-6
    y_mean = Y[tr].mean(axis=0, keepdims=True)
    y_std = Y[tr].std(axis=0, keepdims=True) + 1e-6

    Xn = (X - x_mean) / x_std
    Yn = (Y - y_mean) / y_std

    Xt_tr = torch.from_numpy(Xn[tr].astype(np.float32))
    Yt_tr = torch.from_numpy(Yn[tr].astype(np.float32))
    Xt_te = torch.from_numpy(Xn[te].astype(np.float32))

    in_dim = X.shape[1]
    out_dim = Y.shape[1] if Y.ndim > 1 else 1
    if Y.ndim == 1:
        Yt_tr = Yt_tr.unsqueeze(-1)

    model = MLP(in_dim, out_dim).to(DEVICE)
    opt = torch.optim.Adam(model.parameters(), lr=MLP_LR)
    loss_fn = nn.MSELoss()

    last_loss = float("nan")
    for ep in range(MLP_EPOCHS):
        model.train()
        opt.zero_grad()
        pred = model(Xt_tr)
        loss = loss_fn(pred, Yt_tr)
        loss.backward()
        opt.step()
        last_loss = float(loss.item())

    # Train R²
    model.eval()
    with torch.no_grad():
        y_pred_tr_n = model(Xt_tr).cpu().numpy()
        y_pred_te_n = model(Xt_te).cpu().numpy()
    # Un-standardise
    Y_pred_tr = y_pred_tr_n * y_std + y_mean
    Y_pred_te = y_pred_te_n * y_std + y_mean

    if Y.ndim == 1:
        Y_true_tr = Y[tr].reshape(-1, 1)
        Y_true_te = Y[te].reshape(-1, 1)
    else:
        Y_true_tr = Y[tr]
        Y_true_te = Y[te]

    r2_tr = _r2_score(Y_true_tr, Y_pred_tr)
    r2_te = _r2_score(Y_true_te, Y_pred_te)

    return {
        "label": label,
        "n_train": int(n_tr),
        "n_test": int(n - n_tr),
        "in_dim": in_dim,
        "out_dim": out_dim,
        "r2_train": r2_tr,
        "r2_test": r2_te,
        "overfit_gap": r2_tr - r2_te,
        "final_loss_n": last_loss,
    }


# ─── Main ─────────────────────────────────────────────────────────────

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[R91-D3] Load SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"[R91-D3] {len(agents)} agents loaded")

    print("[R91-D3] Capturing rollouts...")
    all_recs: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        t_s = time.time()
        recs = capture_rollout(scen_name, delta_u, agents)
        print(f"  {scen_name}: {len(recs)} records in {time.time() - t_s:.1f}s")
        all_recs.extend(recs)

    if not all_recs:
        print("FATAL: no records")
        return 1

    # Build feature matrices per agent
    obs_dim = len(all_recs[0]["obs"])
    h_dim = len(all_recs[0]["h_actor"])
    act_dim = len(all_recs[0]["sota_action"])
    print(f"[R91-D3] obs_dim={obs_dim}  h_dim={h_dim}  act_dim={act_dim}  N_records={len(all_recs)}")

    per_agent_r2: dict[str, dict] = {}

    for agent_i in range(4):
        agent_recs = [r for r in all_recs if r["agent"] == agent_i]
        if not agent_recs:
            continue
        X_obs = np.array([r["obs"] for r in agent_recs], dtype=np.float32)
        X_h = np.array([r["h_actor"] for r in agent_recs], dtype=np.float32)
        X_obs_h = np.concatenate([X_obs, X_h], axis=1)
        Y_act = np.array([r["sota_action"] for r in agent_recs], dtype=np.float32)
        Y_next_obs = np.array([r["next_obs"] for r in agent_recs], dtype=np.float32)

        agent_results = {}
        # R1: obs → return for each γ
        for gamma in GAMMAS:
            returns = compute_returns(agent_recs, gamma)
            Y_ret = np.array(returns, dtype=np.float32)
            res = fit_mlp_regressor(X_obs, Y_ret, label=f"R1_obs2return_g{gamma}")
            agent_results[f"R1_g{gamma}"] = res

        # R2: obs → action (memoryless BC)
        agent_results["R2_obs2action"] = fit_mlp_regressor(X_obs, Y_act, label="R2_obs2action")
        # R3: (obs, h) → action (full-info BC)
        agent_results["R3_obs_h2action"] = fit_mlp_regressor(X_obs_h, Y_act, label="R3_obs_h2action")
        # R4: obs → next_obs (forward model)
        agent_results["R4_obs2next_obs"] = fit_mlp_regressor(X_obs, Y_next_obs, label="R4_obs2next_obs")

        per_agent_r2[f"agent_{agent_i}"] = agent_results

    # Cross-agent aggregate (median R²)
    def med(top_key: str) -> float:
        """Median r2_test across agents for a given regressor key."""
        vals = []
        for _ag, results in per_agent_r2.items():
            r = results.get(top_key)
            if isinstance(r, dict):
                v = r.get("r2_test")
                if v is not None:
                    vals.append(float(v))
        return float(np.median(vals)) if vals else float("nan")

    cross = {
        "R1_g0.0_r2_test_median":  med("R1_g0.0"),
        "R1_g0.9_r2_test_median":  med("R1_g0.9"),
        "R1_g0.99_r2_test_median": med("R1_g0.99"),
        "R1_g1.0_r2_test_median":  med("R1_g1.0"),
        "R2_obs2action_r2_test_median":  med("R2_obs2action"),
        "R3_obs_h2action_r2_test_median": med("R3_obs_h2action"),
        "R4_obs2next_obs_r2_test_median": med("R4_obs2next_obs"),
        "h_essentiality_R3_minus_R2_median":
            med("R3_obs_h2action") - med("R2_obs2action"),
    }

    obs_sufficient_value = cross["R1_g0.99_r2_test_median"] >= 0.5
    obs_sufficient_action = cross["R2_obs2action_r2_test_median"] >= 0.7
    h_essential = cross["h_essentiality_R3_minus_R2_median"] >= 0.3
    dynamics_markov = cross["R4_obs2next_obs_r2_test_median"] >= 0.5

    if obs_sufficient_value and obs_sufficient_action:
        gate = "OBS_SUFFICIENT"
        interp = (
            "obs has enough info for V* and π*. Plateau is not obs-ceiling. "
            "R85+ pivots to policy-class (CTDE / attention msg-passing) or "
            "env-floor (D4 disturbance/IC variance). R83 obs aug failure "
            "(W3 0.328 RED) explained: more obs ≠ better policy when "
            "current obs already saturates information channel."
        )
    elif obs_sufficient_value and not obs_sufficient_action and h_essential:
        gate = "H_ESSENTIAL_OBS_VALUE_SUFFICIENT"
        interp = (
            "obs has enough info for V* but the SOTA action requires LSTM h. "
            "R83 obs aug is weakly helpful because critical info is in h, not "
            "in marginal obs slots. R85+ should not chase more obs features; "
            "memory-augmented or attention-aware architectures may help only "
            "if they enrich the latent state beyond LSTM h."
        )
    elif not obs_sufficient_value:
        gate = "OBS_INSUFFICIENT_FOR_VALUE"
        interp = (
            "obs cannot predict discounted return — V*(s) does not factor "
            "through current obs. R83 obs aug **direction** is motivated, "
            "but area_mean_freq / own_action / time alone are not the right "
            "features. R85+ candidates: power-system audit features (line / "
            "load / SBASE residuals from R09 era), reward shape ablation "
            "(PHI_ABS=50 may be the obscuring signal), or reward redesign."
        )
    else:
        gate = "MIXED"
        interp = (
            "Partial sufficiency. Re-run with larger sample budget for "
            "tighter R² estimates before R85+ commit."
        )

    summary = {
        "round": "R91",
        "wave": "W1_D3",
        "title": "Obs sufficiency for V*/π* on R72_w4 SOTA trajectory",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "suffix": "best",
        "env_seed": ENV_SEED,
        "steps_per_scenario": STEPS,
        "scenarios": list(SCENARIOS.keys()),
        "n_records": len(all_recs),
        "obs_dim": obs_dim,
        "h_dim": h_dim,
        "act_dim": act_dim,
        "gammas": GAMMAS,
        "mlp_config": {
            "hidden": MLP_HIDDEN,
            "epochs": MLP_EPOCHS,
            "lr": MLP_LR,
            "dropout": MLP_DROPOUT,
            "train_frac": TRAIN_FRAC,
        },
        "per_agent": per_agent_r2,
        "cross_agent_median": cross,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
            "obs_sufficient_value": bool(obs_sufficient_value),
            "obs_sufficient_action": bool(obs_sufficient_action),
            "h_essential": bool(h_essential),
            "dynamics_markov": bool(dynamics_markov),
        },
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n[R91-D3] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}")
    print()
    print("  Cross-agent median test R²:")
    print(f"    R1 obs→return γ=0    : {cross['R1_g0.0_r2_test_median']:+.3f}")
    print(f"    R1 obs→return γ=0.9  : {cross['R1_g0.9_r2_test_median']:+.3f}")
    print(f"    R1 obs→return γ=0.99 : {cross['R1_g0.99_r2_test_median']:+.3f}")
    print(f"    R1 obs→return γ=1.0  : {cross['R1_g1.0_r2_test_median']:+.3f}")
    print(f"    R2 obs→action        : {cross['R2_obs2action_r2_test_median']:+.3f}")
    print(f"    R3 (obs,h)→action    : {cross['R3_obs_h2action_r2_test_median']:+.3f}")
    print(f"      ΔR3−R2 (h essential): {cross['h_essentiality_R3_minus_R2_median']:+.3f}")
    print(f"    R4 obs→next_obs      : {cross['R4_obs2next_obs_r2_test_median']:+.3f}")
    print()
    print(f"  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
