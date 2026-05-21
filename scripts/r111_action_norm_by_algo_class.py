"""R111 — Control: actor step-0 ||a|| across algo classes (zero ANDES).

R107-W2 (CLM-0193) showed LSTM h=0 produces ||a||=10% of max regardless
of ||obs||. R111 tests whether this saturation deficit is LSTM-specific
or holds across all algo classes. Compare 3 algo classes on the same
step-0-like synthetic obs:

- TD3-MLP (SAC analogue): non-recurrent, ||a|| = tanh(MLP(obs))
- SAC: non-recurrent, ||a|| = mean head of GaussianActor at deterministic eval
- TD3-LSTM: recurrent, ||a|| at h=0 (the bottleneck)

Hypothesis H1 (LSTM-specific saturation deficit):
  LSTM-h=0 ||a||_med ~ 0.15
  MLP / SAC ||a||_med >> 0.15 (e.g., 0.6+)
  ⇒ confirms warm-h_0 fix targets LSTM-specific architectural lag,
  not a general step-0 obs-magnitude limitation.

Hypothesis H0:
  All algos have similar low ||a|| at small obs
  ⇒ saturation deficit is obs-magnitude bound, warm-h_0 only helps
  LSTM at step 0 because MLP / SAC have a different "warm-up"
  problem we haven't characterised.

100 step-0-like obs × R86 6-ckpt set × per-algo branching of the
critic / actor API.

Output: results/r111_action_norm_by_algo_class/summary.json.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if "andes" not in sys.modules:
    sys.modules["andes"] = types.ModuleType("andes")

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402


CKPT_SET: list[tuple[str, str]] = [
    ("r72_w4_lstm_tau001_warmup5_s54",    "td3_lstm",     "r72_w4_lstm_s54"),
    ("r58_paper_strict_pure_td3_lstm_s49", "td3_lstm",     "r58_lstm_s49"),
    ("r58_paper_strict_pure_td3_lstm_s50", "td3_lstm",     "r58_lstm_s50"),
    ("r58_paper_strict_pure_td3_s49",      "td3_mlp",      "r58_td3_mlp_s49"),
    ("r58_paper_strict_pure_sac_s49",      "sac_mlp",      "r58_sac_mlp_s49"),
    ("r63_w4_td3_combo_s49",               "td3_mlp",      "r63_td3_mlp_s49"),
]

N_OBS = 100
OBS_NORM_TARGET = 0.25
OBS_DIM = 7
DEVICE = "cpu"
RNG_SEED = 111

OUT_DIR = ROOT / "results" / "r111_action_norm_by_algo_class"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _sample_obs(n: int, rng: np.random.Generator, norm: float = OBS_NORM_TARGET) -> torch.Tensor:
    raw = rng.normal(0, 1, size=(n, OBS_DIM)).astype(np.float32)
    norms = np.linalg.norm(raw, axis=1, keepdims=True)
    raw = raw / np.maximum(norms, 1e-8) * norm
    return torch.from_numpy(raw).to(DEVICE)


def _action_norm_step0(agent, obs: torch.Tensor) -> np.ndarray:
    """Return ||a||_2 vector (B,) at the deterministic actor evaluation,
    with critic-style "step 0" convention (h_0=0 for recurrent).

    For non-recurrent agents (TD3, SAC) the actor is a `GaussianActor`
    that returns ``(mean, log_std)``. The deployed deterministic action
    is ``tanh(mean)`` (matches `_SACBase.select_action` behaviour). Use
    that to make ||a|| comparable to the tanh-bounded LSTM actor output.
    """
    with torch.no_grad():
        if getattr(agent, "is_recurrent", False):
            h0 = agent.actor.init_hidden(obs.shape[0], DEVICE)
            a, _ = agent.actor(obs, h0)
        else:
            out = agent.actor(obs)
            mean = out[0] if isinstance(out, tuple) else out
            a = torch.tanh(mean)
    return a.norm(dim=-1).cpu().numpy()


def main() -> None:
    print(f"R111: step-0 ||a|| comparison across algo classes")
    print(f"  ||obs||={OBS_NORM_TARGET}, N={N_OBS} obs × N=6 ckpts × 4 agents = 2400 forward passes\n")

    rng = np.random.default_rng(RNG_SEED)
    obs = _sample_obs(N_OBS, rng)

    per_ckpt: list[dict] = []
    for ckpt_dir, algo, label in CKPT_SET:
        path = ROOT / "results" / ckpt_dir
        if not path.exists():
            print(f"  SKIP missing: {ckpt_dir}")
            continue
        agents = load_agents(path, suffix="best")
        norms_all = []
        for ag in agents:
            norms_all.extend(_action_norm_step0(ag, obs).tolist())
        norms_all = np.array(norms_all)
        rec = {
            "ckpt": label,
            "algo_class": algo,
            "n_samples": len(norms_all),
            "norm_median": float(np.median(norms_all)),
            "norm_p10": float(np.percentile(norms_all, 10)),
            "norm_p90": float(np.percentile(norms_all, 90)),
            "norm_pct_max_median": float(np.median(norms_all) / np.sqrt(2) * 100),
        }
        per_ckpt.append(rec)
        print(f"  {label:25s} algo={algo:10s} ||a||_med={rec['norm_median']:.3f} "
              f"({rec['norm_pct_max_median']:5.1f}% of max)  p10={rec['norm_p10']:.3f} p90={rec['norm_p90']:.3f}")

    # Aggregate by algo class
    by_algo: dict[str, list[float]] = {}
    for r in per_ckpt:
        by_algo.setdefault(r["algo_class"], []).append(r["norm_pct_max_median"])

    print("\n  per-algo-class median (of ckpt medians):")
    algo_agg = {}
    for algo, vals in by_algo.items():
        algo_agg[algo] = float(np.median(vals))
        print(f"    {algo}: median ||a||_pct_max = {algo_agg[algo]:5.1f}%")

    # H1 vs H0
    lstm_med = algo_agg.get("td3_lstm", float("nan"))
    mlp_meds = [v for k, v in algo_agg.items() if k != "td3_lstm"]
    if mlp_meds and not np.isnan(lstm_med):
        non_lstm_med = float(np.median(mlp_meds))
        gap = non_lstm_med - lstm_med
        if gap > 20:
            verdict = f"H1 (LSTM-specific): LSTM={lstm_med:.1f}% << non-LSTM={non_lstm_med:.1f}% (gap {gap:.1f}pp)"
        elif gap < -10:
            verdict = f"REVERSED: LSTM has higher step-0 ||a|| than non-LSTM"
        else:
            verdict = f"H0 (similar): LSTM={lstm_med:.1f}% ~ non-LSTM={non_lstm_med:.1f}% (gap {gap:.1f}pp)"
    else:
        verdict = "insufficient data"

    summary = {
        "round": "R111",
        "kind": "step0_action_norm_by_algo_class",
        "obs_norm_target": OBS_NORM_TARGET,
        "n_obs_per_ckpt_agent": N_OBS,
        "per_ckpt": per_ckpt,
        "per_algo_class_median_pct_max": algo_agg,
        "verdict": verdict,
        "interpretation": (
            "Compares step-0 ||a||_2 across LSTM vs MLP / SAC actor "
            "classes on identical step-0-like synthetic obs. Confirms "
            "(or refutes) whether warm-h_0 fix targets a LSTM-specific "
            "architectural deficit vs a general step-0 saturation issue."
        ),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\n{verdict}")
    print(f"\nWritten: {OUT_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
