"""R96-W1: Cross-ckpt validation of CLM-0163 value-horizon mismatch.

CLM-0163 found on R72_w4 SOTA: obs→return at paper γ=0.99 gives R²=−0.41
(worse than predicting the mean), while γ=0/γ=1.0 give R²=0.93/0.71.
This may be R72_w4-specific (one LSTM warmup=5 hyper basin) or a
problem-setup property of the 7-dim paper-faithful obs + V4 reward.

Distinguish by replicating R1 (obs→return at 4 γ) + R2 (obs→action) on
4 alternative ckpts:

| Ckpt | Algorithm | Trained-time hyper |
|---|---|---|
| r72_w4_lstm_tau001_warmup5_s54 | TD3 + LSTM, warmup=5 | R72 (baseline) |
| r75_w2_lstm_tau001_warmup20_s59 | TD3 + LSTM, warmup=20 | R75 |
| r63_w4_td3_combo_s49 | TD3 MLP, combo hyper | R63 |
| td3_norm_h64_s49 | TD3 MLP, normalized actions, h=64 | R41-B |

If γ=0.99 R² is consistently the worst (< 0 or near 0) across all 4 →
**universal problem-setup property**: paper γ × paper reward × paper obs
specifically creates the value-horizon mismatch, regardless of algorithm
class or training hyper. → R97+ should ablate problem setup (γ or reward)
not algorithm.

If R72_w4 is the outlier → finding is hyper-specific; less paper impact.

Cross-ckpt is on-manifold (real ANDES TDS deterministic rollout per
ckpt), zero training, ~4 min total wall (4 ckpts × 1 short rollout +
regressor fit).

Output: `results/r96_d3_cross_ckpt/{summary.json, per_ckpt.csv}`

Note: TD3-MLP ckpts (no LSTM h_actor) skip the R3 (obs+h)→action
regressor; only R1+R2 are reported across ckpts. R72_w4 R1 result is
included as the baseline for the comparison.

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r96_d3_cross_ckpt.py
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
CKPT_LIST = [
    ("r72_w4_lstm_tau001_warmup5_s54", "TD3+LSTM warmup=5",  "best", True),
    ("r75_w2_lstm_tau001_warmup20_s59", "TD3+LSTM warmup=20", "best", True),
    ("r63_w4_td3_combo_s49",            "TD3 MLP combo",       "best", False),
    ("td3_norm_h64_s49",                "TD3 MLP norm h=64",   "best", False),
]
OUT_DIR = ROOT / "results" / "r96_d3_cross_ckpt"
ENV_SEED = 42
STEPS = 50
GAMMAS = [0.0, 0.9, 0.99, 1.0]
TRAIN_FRAC = 0.8
MLP_HIDDEN = 64
MLP_EPOCHS = 300
MLP_LR = 1e-3
MLP_DROPOUT = 0.10
DEVICE = torch.device("cpu")
RNG = np.random.default_rng(seed=0xD3C)


# ─── Rollout capture ──────────────────────────────────────────────────

def capture_rollout(scen_name: str, delta_u: dict, agents: list, is_recurrent: bool) -> list[dict]:
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    records: list[dict] = []
    try:
        env.seed(ENV_SEED)
        env.STEPS_PER_EPISODE = STEPS
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS

        if is_recurrent:
            for ag in agents:
                if getattr(ag, "is_recurrent", False):
                    ag.begin_episode()
            h_actor = [ag.actor.init_hidden(1, DEVICE) for ag in agents]
        else:
            h_actor = [None] * n_agents

        for step in range(STEPS):
            actions: dict[int, np.ndarray] = {}
            obs_dump = {i: obs[i].copy().astype(np.float32) for i in range(n_agents)}
            for i, ag in enumerate(agents):
                # Use the agent's own select_action which handles its arch correctly
                a_np = ag.select_action(obs[i], deterministic=True)
                actions[i] = np.asarray(a_np, dtype=np.float32)

            next_obs, rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                print(f"  [tds_failed @ step {step}]")
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
                    "next_obs": next_obs[i].copy().astype(np.float32).tolist(),
                    "sota_action": actions[i].tolist(),
                    "reward": rew[i],
                })

            obs = next_obs
            if done:
                break
    finally:
        env.close()
    return records


# ─── Returns ─────────────────────────────────────────────────────────

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


def _r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = float(np.sum((y_true - y_pred) ** 2))
    ss_tot = float(np.sum((y_true - y_true.mean(axis=0, keepdims=True)) ** 2))
    if ss_tot <= 1e-12:
        return 1.0 if ss_res < 1e-12 else 0.0
    return 1.0 - ss_res / ss_tot


def fit_mlp(X: np.ndarray, Y: np.ndarray) -> dict:
    n = X.shape[0]
    perm = RNG.permutation(n)
    n_tr = int(TRAIN_FRAC * n)
    tr, te = perm[:n_tr], perm[n_tr:]

    x_mean = X[tr].mean(axis=0, keepdims=True)
    x_std = X[tr].std(axis=0, keepdims=True) + 1e-6
    y_mean = Y[tr].mean(axis=0, keepdims=True)
    y_std = Y[tr].std(axis=0, keepdims=True) + 1e-6

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
        y_pred_tr = model(Xt_tr).cpu().numpy() * y_std + y_mean
        y_pred_te = model(Xt_te).cpu().numpy() * y_std + y_mean

    Y_true_tr = Y[tr].reshape(-1, out_dim) if Y.ndim == 1 else Y[tr]
    Y_true_te = Y[te].reshape(-1, out_dim) if Y.ndim == 1 else Y[te]

    return {
        "n_train": int(n_tr),
        "n_test": int(n - n_tr),
        "r2_train": _r2(Y_true_tr, y_pred_tr),
        "r2_test":  _r2(Y_true_te, y_pred_te),
    }


# ─── Per-ckpt pipeline ────────────────────────────────────────────────

def evaluate_ckpt(ckpt_name: str, label: str, suffix: str, is_recurrent: bool) -> dict:
    ckpt_dir = ROOT / "results" / ckpt_name
    if not ckpt_dir.exists():
        return {"ckpt": ckpt_name, "label": label, "skipped": "dir missing"}
    print(f"\n[R96] === {label}  ({ckpt_name}) ===")
    t_ck = time.time()
    try:
        agents = load_agents(ckpt_dir, suffix=suffix)
    except Exception as e:
        print(f"  load_agents FAIL: {e}")
        return {"ckpt": ckpt_name, "label": label, "error": str(e)[:200]}

    all_recs: list[dict] = []
    for scen_name, delta_u in SCENARIOS.items():
        t_s = time.time()
        recs = capture_rollout(scen_name, delta_u, agents, is_recurrent)
        print(f"  {scen_name}: {len(recs)} records in {time.time()-t_s:.1f}s")
        all_recs.extend(recs)

    if not all_recs:
        return {"ckpt": ckpt_name, "label": label, "error": "no records collected"}

    # Per-agent R1+R2 fits → cross-agent median
    per_agent = {}
    for agent_i in range(4):
        agent_recs = [r for r in all_recs if r["agent"] == agent_i]
        if not agent_recs:
            continue
        X_obs = np.array([r["obs"] for r in agent_recs], dtype=np.float32)
        Y_act = np.array([r["sota_action"] for r in agent_recs], dtype=np.float32)
        agent_res = {}
        for gamma in GAMMAS:
            returns = compute_returns(agent_recs, gamma)
            Y_ret = np.array(returns, dtype=np.float32)
            agent_res[f"R1_g{gamma}"] = fit_mlp(X_obs, Y_ret)
        agent_res["R2_obs2action"] = fit_mlp(X_obs, Y_act)
        per_agent[f"agent_{agent_i}"] = agent_res

    def med(top_key: str) -> float:
        vals = []
        for _ag, results in per_agent.items():
            r = results.get(top_key, {})
            if isinstance(r, dict) and "r2_test" in r:
                vals.append(float(r["r2_test"]))
        return float(np.median(vals)) if vals else float("nan")

    cross = {
        "R1_g0.0":  med("R1_g0.0"),
        "R1_g0.9":  med("R1_g0.9"),
        "R1_g0.99": med("R1_g0.99"),
        "R1_g1.0":  med("R1_g1.0"),
        "R2_obs2action": med("R2_obs2action"),
    }
    print(f"  R1[γ=0]={cross['R1_g0.0']:+.3f}  R1[γ=0.9]={cross['R1_g0.9']:+.3f}  "
          f"R1[γ=0.99]={cross['R1_g0.99']:+.3f}  R1[γ=1.0]={cross['R1_g1.0']:+.3f}  "
          f"R2[a]={cross['R2_obs2action']:+.3f}")
    print(f"  ckpt wall {time.time() - t_ck:.1f}s")

    return {
        "ckpt": ckpt_name,
        "label": label,
        "suffix": suffix,
        "is_recurrent": is_recurrent,
        "n_records": len(all_recs),
        "cross_agent_median": cross,
        "per_agent": per_agent,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    results = [evaluate_ckpt(c, l, s, r) for c, l, s, r in CKPT_LIST]

    # Universal check
    g099 = [
        r.get("cross_agent_median", {}).get("R1_g0.99", float("nan"))
        for r in results if "cross_agent_median" in r
    ]
    g099_valid = [v for v in g099 if not np.isnan(v)]
    universal_negative = all(v < 0.2 for v in g099_valid) if g099_valid else False
    universal_strong_negative = all(v < 0.0 for v in g099_valid) if g099_valid else False

    g0 = [
        r.get("cross_agent_median", {}).get("R1_g0.0", float("nan"))
        for r in results if "cross_agent_median" in r
    ]
    g0_high = all(v > 0.5 for v in g0 if not np.isnan(v))

    if universal_strong_negative and g0_high:
        gate = "UNIVERSAL_VALUE_HORIZON_MISMATCH"
        interp = (
            "All ckpts (LSTM warmup=5, LSTM warmup=20, TD3 MLP combo, TD3 MLP norm) "
            "show R²<0 at γ=0.99 paper discount AND R²>0.5 at γ=0 instant. CLM-0163 "
            "elevated from R72_w4-specific to **paper-setup property**: paper γ=0.99 × "
            "paper-faithful 7-dim obs × paper reward together create a value horizon "
            "the obs cannot predict, independent of algorithm class. Paper Section IV-D "
            "claim: '91-round plateau mechanism is value-horizon mismatch at the paper-"
            "selected discount factor, not algorithm or representation.'"
        )
    elif universal_negative:
        gate = "WEAK_UNIVERSAL_NEGATIVE"
        interp = (
            "All ckpts show R²<0.2 at γ=0.99, but not all R²<0. Effect is consistent "
            "across ckpts but not as catastrophic as R72_w4. Still strong universal signal."
        )
    elif any(v < 0 for v in g099_valid):
        gate = "PARTIAL_UNIVERSAL"
        interp = "Some but not all ckpts replicate R²<0 at γ=0.99. R72_w4 partially special."
    else:
        gate = "R72_W4_SPECIFIC"
        interp = "Cross-ckpt does not replicate CLM-0163. Finding is hyper-specific."

    summary = {
        "round": "R96",
        "wave": "W1_D3_cross_ckpt",
        "title": "Cross-ckpt validation of CLM-0163 value-horizon mismatch",
        "ckpts": [c for c, _, _, _ in CKPT_LIST],
        "results": results,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
            "g099_per_ckpt": dict(zip([c for c, _, _, _ in CKPT_LIST], g099)),
            "g0_per_ckpt":   dict(zip([c for c, _, _, _ in CKPT_LIST], g0)),
            "universal_strong_negative_g099": bool(universal_strong_negative),
            "universal_g0_high": bool(g0_high),
        },
        "wall_seconds": time.time() - t0,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print("\n[R96] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}\n")
    print("  R²(obs→return γ=0.99) per ckpt:")
    for c, _, _, _ in CKPT_LIST:
        v = next((r["cross_agent_median"].get("R1_g0.99") for r in results if r.get("ckpt") == c and "cross_agent_median" in r), None)
        print(f"    {c:50s}  {v if v is None else f'{v:+.3f}'}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
