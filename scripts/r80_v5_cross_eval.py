"""R80 Cycle 4 — V4-trained SOTA ckpt cross-eval on V4 / V5_w2_only / V5_gencls.

RED expectation (behavior under test):
    "Same R72_w4 LSTM ckpt (trained on V4 plant) 在 V5_w2_only plant 上 eval
    出来的 11-axis geo, 跟 V4 plant 上的 geo 比 — 提升 ≥ 0.05 → 进 Phase C 训练;
    持平 (|Δ| < 0.05) → C4 negative finding; 下降 ≥ 0.05 → 仍进 Phase C 但
    要重训才行."

不动 paper_path.run_scenario (paper-cited Asset 4). 本脚本 inline 一份
parameterized eval loop, 改 env_cls / env_cfg.

每个 env 产物落到 results/r80_v5_cross_eval/<env_label>/, 含:
    - no_control_load_step_{1,2}.json    (axis 8 reference)
    - ckpt_R72w4_load_step_{1,2}.json    (eval traces)
    - summary.json                        (score_trace_files 输出)

最终 r80_v5_cross_eval_summary.json 汇总 3 env 的 geo + cum_rf.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.env.andes.andes_vsg_env_v5 import AndesMultiVSGEnvV5  # noqa: E402
from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.env.andes.v5_config import V5Config  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    zero_action_fn,
)
from andes_rl_kundur.evaluation.summary import format_headline, score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402


CKPT_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
CKPT_SUFFIX = "best"
OUT_ROOT = ROOT / "results" / "r80_v5_cross_eval"
EVAL_SEED = 42
STEPS = 150  # 30 s @ DT=0.2, 和 eval_ddic.py 一致


# ─── inline parameterized run_scenario (paper_path.run_scenario 的 env-pluggable 版) ──

def _run_scenario(
    env_cls,
    env_cfg,
    scen_name: str,
    delta_u: dict[str, Any],
    *,
    action_fn: Callable,
    label: str,
    seed: int = EVAL_SEED,
    steps: int = STEPS,
) -> dict[str, Any]:
    env = env_cls(random_disturbance=False, comm_fail_prob=0.0, config=env_cfg)
    traces: list[dict[str, Any]] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)
        n_agents = env.N_AGENTS
        f_nom = env.FN

        for step in range(steps):
            actions = action_fn(step, obs, n_agents)
            obs, _rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                break
            freq_hz = info["freq_hz"].astype(float).tolist()
            delta_f = [(f - f_nom) for f in freq_hz]
            f_bar = float(np.mean(freq_hz))
            step_rf = float(np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f]))
            cum_rf -= step_rf
            max_df = max(max_df, float(np.max(np.abs(delta_f))))
            osc_accum += float(np.std(delta_f))
            traces.append({
                "step": step, "t": float(info["time"]),
                "freq_hz": freq_hz, "f_bar": f_bar, "step_rf": step_rf,
                "delta_P_es": info["P_es"].astype(float).tolist(),
                "delta_f_es": delta_f,
                "M_es": info["M_es"].astype(float).tolist(),
                "D_es": info["D_es"].astype(float).tolist(),
                "delta_M": info["delta_M"].astype(float).tolist(),
                "delta_D": info["delta_D"].astype(float).tolist(),
            })
            if done:
                break
    finally:
        env.close()

    return {
        "controller": label, "scenario": scen_name,
        "env_version": env_cls.__name__,
        "cum_rf_total": cum_rf, "max_df": max_df, "osc": osc_accum,
        "n_steps": len(traces), "traces": traces,
    }


# ─── 主流程 ──────────────────────────────────────────────────────────────

def main():
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"[cross-eval] loading R72_w4 LSTM ckpt from {CKPT_DIR}")
    agents = load_agents(CKPT_DIR, suffix=CKPT_SUFFIX)
    ckpt_action_fn = deterministic_actor_action_fn(agents)
    ckpt_label = "R72w4_LSTM_s54"

    env_configs = [
        ("v4_baseline",    AndesMultiVSGEnvV4, V4Config.paper_faithful()),
        ("v5_w2_only",     AndesMultiVSGEnvV5, V5Config.v5_default()),
        ("v5_gencls_fall", AndesMultiVSGEnvV5, V5Config.v4_plant_fallback()),
    ]

    grand_summary: dict[str, Any] = {
        "ckpt": str(CKPT_DIR.name),
        "ckpt_suffix": CKPT_SUFFIX,
        "steps": STEPS, "seed": EVAL_SEED,
        "envs": {},
    }

    for env_label, env_cls, env_cfg in env_configs:
        env_out = OUT_ROOT / env_label
        env_out.mkdir(parents=True, exist_ok=True)
        print(f"\n========== env={env_label} ==========")

        env_section: dict[str, Any] = {"no_control": {}, "ckpt": {}, "summary": None}

        # Per-env no-control reference (axis 8 needs sibling no_control_<scen>.json)
        nc_paths: dict[str, Path] = {}
        for scen, du in SCENARIOS.items():
            try:
                rep = _run_scenario(env_cls, env_cfg, scen, du,
                                    action_fn=zero_action_fn, label="no_control")
                p = env_out / f"no_control_{scen}.json"
                p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
                nc_paths[scen] = p
                env_section["no_control"][scen] = {
                    "max_df": rep["max_df"], "n_steps": rep["n_steps"],
                    "cum_rf_total": rep["cum_rf_total"],
                }
                print(f"  no_ctrl/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
            except Exception as e:
                env_section["no_control"][scen] = {"error": f"{type(e).__name__}: {e}",
                                                    "tb": traceback.format_exc().splitlines()[-6:]}
                print(f"  no_ctrl/{scen}: ERROR {e}")

        # Ckpt eval
        ckpt_paths: dict[str, Path] = {}
        for scen, du in SCENARIOS.items():
            try:
                rep = _run_scenario(env_cls, env_cfg, scen, du,
                                    action_fn=ckpt_action_fn, label=ckpt_label)
                p = env_out / f"ckpt_{ckpt_label}_{scen}.json"
                p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
                ckpt_paths[scen] = p
                env_section["ckpt"][scen] = {
                    "max_df": rep["max_df"], "n_steps": rep["n_steps"],
                    "cum_rf_total": rep["cum_rf_total"],
                }
                print(f"  ckpt/{scen}: max_df={rep['max_df']:.4f} n={rep['n_steps']}")
            except Exception as e:
                env_section["ckpt"][scen] = {"error": f"{type(e).__name__}: {e}",
                                             "tb": traceback.format_exc().splitlines()[-6:]}
                print(f"  ckpt/{scen}: ERROR {e}")

        # Score the ckpt traces against the env-specific no_control reference
        if ckpt_paths:
            try:
                env_section["summary"] = score_trace_files(
                    ckpt_paths, label=ckpt_label, is_ddic=True,
                )
                print(f"  summary: {format_headline(env_section['summary'])}")
            except Exception as e:
                env_section["summary"] = {"error": f"{type(e).__name__}: {e}",
                                          "tb": traceback.format_exc().splitlines()[-6:]}
                print(f"  summary: ERROR {e}")

        grand_summary["envs"][env_label] = env_section
        # Incremental flush
        (OUT_ROOT / "r80_v5_cross_eval_summary.json").write_text(
            json.dumps(grand_summary, indent=2, default=str), encoding="utf-8"
        )

    # Final GATE C decision
    v4_geo = (grand_summary["envs"].get("v4_baseline", {}).get("summary") or {}).get("geo")
    v5_geo = (grand_summary["envs"].get("v5_w2_only", {}).get("summary") or {}).get("geo")
    gate_c = "N/A"
    if isinstance(v4_geo, (int, float)) and isinstance(v5_geo, (int, float)):
        diff = v5_geo - v4_geo
        if diff >= 0.05:
            gate_c = f"GO Phase C (V5 +{diff:.4f} vs V4)"
        elif diff <= -0.05:
            gate_c = f"GO Phase C reverse (V5 {diff:.4f} vs V4)"
        else:
            gate_c = f"C4 negative finding (|Δ|={abs(diff):.4f} < 0.05)"
    grand_summary["gate_c_decision"] = gate_c
    (OUT_ROOT / "r80_v5_cross_eval_summary.json").write_text(
        json.dumps(grand_summary, indent=2, default=str), encoding="utf-8"
    )
    print(f"\n[GATE C] {gate_c}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
