"""R13 — Settling-time reward MVV probe (方向 4).

Goal: 验在线计算 t_settling 从 freq trajectory 是否可行 + 量级 sanity 跟 r^f / r^h
能否平衡 (即 r_settling 不会主导 reward).

定义: t_settling = 第一个时刻 t* 使得 |Δf(τ)| < threshold ∀ τ ≥ t*. 若一直没 settle
return PROBE_DURATION (penalty 上限).

不训练. 跑 30 step zero-action LS1, episode 末计算一次 t_settling 量级.

Verdict:
  t_settling computable=False  → INFEASIBLE
  t_settling = full duration   → trajectory 没 settle, reward 接近常数 (no signal)
  r_settling 量级 >> r^f/r^h   → MARGINAL, 难调权重
  r_settling 量级 ≈ r^f/r^h    → FEASIBLE
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from env.andes.andes_vsg_env_v2 import AndesMultiVSGEnvV2  # noqa: E402

LS1_DELTA_U = {"PQ_Bus14": -2.48}
PROBE_STEPS = 150  # 30s @ DT=0.2 (paper Fig.7 量级, 旧 30 step=6s 太短 NO_SIGNAL)
H_FORCED = 6.5
SETTLE_THRESHOLD_HZ = 0.02   # paper-spec settling band


def compute_settling(df_traj: np.ndarray, dt: float, threshold: float) -> float:
    """Online t_settling from |Δf| trajectory. Walk back from end."""
    T = len(df_traj)
    last_violation = -1
    for k in range(T - 1, -1, -1):
        if abs(df_traj[k]) >= threshold:
            last_violation = k
            break
    if last_violation < 0:
        return 0.0  # never violated (already settled at t=0)
    if last_violation == T - 1:
        return T * dt  # never settled within window
    return (last_violation + 1) * dt


def main() -> int:
    out: dict[str, Any] = {
        "probe": "r13_settling_reward",
        "version": 1,
        "settle_threshold_hz": SETTLE_THRESHOLD_HZ,
    }
    try:
        env = AndesMultiVSGEnvV2(random_disturbance=False, comm_fail_prob=0.0)
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * H_FORCED)
        # Override episode length so done flag does NOT early-terminate
        # the long settling-time trace (R13 long-trace fix, 2026-05-07).
        env.STEPS_PER_EPISODE = PROBE_STEPS
        env.reset(delta_u=LS1_DELTA_U)
        dt = env.DT
        out["dt"] = float(dt)

        df_traj = []
        rf_per_step = []
        rh_per_step = []
        rd_per_step = []
        for step in range(PROBE_STEPS):
            actions = {i: np.zeros(2, dtype=np.float32) for i in range(env.N_AGENTS)}
            try:
                _, _, done, info = env.step(actions)
            except Exception as e:
                out["step_err"] = f"step {step}: {str(e)[:120]}"
                break
            if info.get("tds_failed"):
                out["tds_failed_step"] = step
                break
            df_traj.append(info["max_freq_deviation_hz"])
            rf_per_step.append(info["r_f"])
            rh_per_step.append(info["r_h"])
            rd_per_step.append(info["r_d"])
            if done:
                break
        env.close()

        if not df_traj:
            out["computable"] = False
            out["verdict"] = "INFEASIBLE — no steps completed"
            _save(out)
            return 0

        df_arr = np.array(df_traj)
        out["computable"] = True
        out["n_steps"] = len(df_arr)
        out["max_df"] = float(df_arr.max())
        out["final_df"] = float(df_arr[-1])

        t_settle = compute_settling(df_arr, dt, SETTLE_THRESHOLD_HZ)
        out["t_settling_s"] = float(t_settle)
        out["episode_duration_s"] = float(out["n_steps"] * dt)

        # Reward magnitude comparison (per-step sums, not per-agent)
        rf_arr = np.array(rf_per_step)
        rh_arr = np.array(rh_per_step)
        rd_arr = np.array(rd_per_step)
        out["r_f_sum_episode"] = float(rf_arr.sum())
        out["r_h_sum_episode"] = float(rh_arr.sum())
        out["r_d_sum_episode"] = float(rd_arr.sum())
        out["r_f_per_step_mean_abs"] = float(np.abs(rf_arr).mean())
        out["r_h_per_step_mean_abs"] = float(np.abs(rh_arr).mean())
        out["r_d_per_step_mean_abs"] = float(np.abs(rd_arr).mean())

        # Proposed r_settling formulation: -alpha * (t_settling / max_t)
        # 量级 baseline: 让 r_settling ~ -alpha at worst case (never settle)
        existing_max = max(out["r_f_per_step_mean_abs"],
                           out["r_h_per_step_mean_abs"],
                           out["r_d_per_step_mean_abs"], 1e-9)
        # episode-level r_settling sum (not per-step), match Eq.15-17 form
        out["proposed_r_settling_episode_baseline"] = -1.0 * (t_settle / out["episode_duration_s"])

        # Verdict
        if t_settle == out["episode_duration_s"]:
            out["verdict"] = (
                f"NO_SIGNAL — never settled within {out['episode_duration_s']:.1f}s; "
                "r_settling 永远是 penalty 上限, 训练梯度为 0. 需要更长 PROBE_STEPS 或 less aggressive disturbance."
            )
        elif t_settle == 0.0:
            out["verdict"] = "FALSE_POSITIVE — t_settling=0, threshold 太松或 disturbance 太弱"
        else:
            out["verdict"] = (
                f"FEASIBLE — t_settling={t_settle:.2f}s ({t_settle/out['episode_duration_s']*100:.0f}% of episode), "
                f"建议 alpha ≈ {existing_max:.2e} 让 r_settling 跟 r^f/r^h 同量级"
            )

        print("=== R13 settling-time reward MVV ===")
        print(f"  steps                : {out['n_steps']}, dt={dt:.3f}s, episode={out['episode_duration_s']:.2f}s")
        print(f"  max_df / final_df    : {out['max_df']:.3f} / {out['final_df']:.3f}")
        print(f"  t_settling           : {t_settle:.2f}s")
        print(f"  r^f/r^h/r^d episode  : {out['r_f_sum_episode']:.3e} / {out['r_h_sum_episode']:.3e} / {out['r_d_sum_episode']:.3e}")
        print(f"  r^f/r^h/r^d per-step : {out['r_f_per_step_mean_abs']:.3e} / {out['r_h_per_step_mean_abs']:.3e} / {out['r_d_per_step_mean_abs']:.3e}")
        print(f"  verdict              : {out['verdict']}")
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
        print(f"R13 ERROR: {out['error']}")

    _save(out)
    return 0


def _save(out: dict) -> None:
    p = ROOT / "results" / "research_loop" / "r13_settling_reward_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")


if __name__ == "__main__":
    sys.exit(main())
