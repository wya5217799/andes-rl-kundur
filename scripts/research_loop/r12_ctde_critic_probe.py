"""R12 — CTDE critic shape MVV probe (方向 3).

Goal: 验 CTDE critic input dim = 4×OBS_DIM + 4×ACTION_DIM = 36 (Kundur) 计算可行,
build_mlp 不报错, forward 量级合理, parameter count 增加倍数可接受.

不训练. 只 dummy tensor forward + parameter count diff.

Verdict matrix:
  forward fails           → INFEASIBLE
  param count > 10× local → MARGINAL (训练成本爆炸)
  forward OK + < 4×       → FEASIBLE
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agents.networks import DoubleQCritic  # noqa: E402

# Kundur defaults (per env/andes/andes_vsg_env.py)
N_AGENTS = 4
OBS_DIM_LOCAL = 7   # per agent (4 freq features + 3 self) — V2 default
ACTION_DIM_LOCAL = 2  # delta_M, delta_D
HIDDEN = [256, 256]


def count_params(net) -> int:
    return sum(p.numel() for p in net.parameters() if p.requires_grad)


def main() -> int:
    out: dict[str, Any] = {"probe": "r12_ctde_critic_shape", "version": 1}
    try:
        # Local (current paper-faithful)
        local_critic = DoubleQCritic(OBS_DIM_LOCAL, ACTION_DIM_LOCAL, HIDDEN)
        local_obs = torch.randn(8, OBS_DIM_LOCAL)
        local_act = torch.randn(8, ACTION_DIM_LOCAL)
        q1_local, q2_local = local_critic(local_obs, local_act)
        out["local"] = {
            "obs_dim": OBS_DIM_LOCAL,
            "action_dim": ACTION_DIM_LOCAL,
            "params": count_params(local_critic),
            "q_shape": list(q1_local.shape),
            "q_mean": float(q1_local.mean()),
            "q_std": float(q1_local.std()),
        }

        # CTDE (global)
        global_obs_dim = N_AGENTS * OBS_DIM_LOCAL      # 28
        global_act_dim = N_AGENTS * ACTION_DIM_LOCAL    # 8
        global_critic = DoubleQCritic(global_obs_dim, global_act_dim, HIDDEN)
        global_obs = torch.randn(8, global_obs_dim)
        global_act = torch.randn(8, global_act_dim)
        q1_global, q2_global = global_critic(global_obs, global_act)
        out["global"] = {
            "obs_dim": global_obs_dim,
            "action_dim": global_act_dim,
            "params": count_params(global_critic),
            "q_shape": list(q1_global.shape),
            "q_mean": float(q1_global.mean()),
            "q_std": float(q1_global.std()),
        }

        # Diff
        param_ratio = out["global"]["params"] / out["local"]["params"]
        out["param_ratio_global_over_local"] = float(param_ratio)
        out["any_nan"] = bool(
            torch.isnan(q1_global).any() or torch.isnan(q2_global).any()
        )

        # Code change scope estimate
        out["code_change_scope"] = {
            "files": [
                "agents/sac.py (SACAgent.__init__: critic obs_dim arg)",
                "agents/ma_manager.py (pass global_obs_dim to critic only)",
                "scenarios/kundur/train_andes*.py (collect global obs+action before critic update)",
            ],
            "estimated_lines": "~30-50 LOC, no new files",
        }

        # Verdict
        if out["any_nan"]:
            out["verdict"] = "INFEASIBLE — NaN in dummy forward (numerical issue)"
        elif param_ratio > 10:
            out["verdict"] = f"MARGINAL — param_ratio={param_ratio:.2f}× > 10×, training cost 爆炸"
        elif param_ratio > 4:
            out["verdict"] = f"BORDERLINE — param_ratio={param_ratio:.2f}× (4-10×), need GPU"
        else:
            out["verdict"] = (
                f"FEASIBLE — global critic params {out['global']['params']} vs local "
                f"{out['local']['params']} ({param_ratio:.2f}×), forward shape ok, "
                "CPU 训练可承受"
            )

        print("=== R12 CTDE critic shape MVV ===")
        print(f"  Local critic   obs={OBS_DIM_LOCAL} act={ACTION_DIM_LOCAL} params={out['local']['params']}")
        print(f"  Global critic  obs={global_obs_dim} act={global_act_dim} params={out['global']['params']}")
        print(f"  param ratio    : {param_ratio:.2f}×")
        print(f"  q_global mean/std: {out['global']['q_mean']:.3e} / {out['global']['q_std']:.3e}")
        print(f"  verdict        : {out['verdict']}")
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
        print(f"R12 ERROR: {out['error']}")
        print(out["traceback"])

    p = ROOT / "results" / "research_loop" / "r12_ctde_critic_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
