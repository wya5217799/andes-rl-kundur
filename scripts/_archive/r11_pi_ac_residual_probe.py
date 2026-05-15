"""R11 — Physics-Informed Actor-Critic (PI-AC) residual MVV probe.

方向 2 of 优化方向.md: SAC critic loss 加 swing equation residual 正则项

    J_physics = || M · ω̇ + D·(ω-1) - (Pm - Pe) ||²

MVV question: 残差从 env state 算得出, 量级合理, 不 NaN/inf?
- 不训练. 跑 30 step zero-action LS1, 每步算 J_physics, 看分布.

Verdict matrix:
  computable=False                 → INFEASIBLE (fields missing)
  median > 1.0 sys_pu²             → magnitude太大, λ 难选
  median < 1e-6 sys_pu²            → 信号太弱, 正则项无效
  1e-4 ≤ median ≤ 1.0              → FEASIBLE, λ ≈ 1/median 量级
  any NaN/inf                      → numerical 不稳定

Run: /home/wya/andes_venv/bin/python scripts/research_loop/r11_pi_ac_residual_probe.py
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
from probes.andes_common import introspect_model, safe_get, try_read_v  # noqa: E402

LS1_DELTA_U = {"PQ_Bus14": -2.48}
PROBE_STEPS = 30
H_FORCED = 6.5
PM_CAND = ("tm", "Pm", "pm0", "pm")


def main() -> int:
    out: dict[str, Any] = {"probe": "r11_pi_ac_residual", "version": 1}
    try:
        env = AndesMultiVSGEnvV2(random_disturbance=False, comm_fail_prob=0.0)
        env.seed(42)
        env.M0 = np.full(env.N_AGENTS, 2.0 * H_FORCED)
        env.reset(delta_u=LS1_DELTA_U)
        ss = env.ss

        # Find Pm-like attribute on GENCLS
        pm_attr, pm_t0 = try_read_v(safe_get(ss, "GENCLS"), PM_CAND)
        out["pm_attr"] = pm_attr
        out["pm_t0"] = pm_t0
        out["gencls_dae_vars"] = [
            v["attr"] for v in introspect_model(ss, "GENCLS").get("readable_vars", [])
            if v.get("kind") in {"Algeb", "State", "ExtAlgeb", "ExtState"}
        ]

        if pm_attr is None:
            out["computable"] = False
            out["verdict"] = "INFEASIBLE — GENCLS Pm-like field not found"
            print(f"r11 verdict: {out['verdict']}")
            print(f"  GENCLS DAE vars: {out['gencls_dae_vars']}")
            _save(out)
            return 0

        residuals = []  # list of per-step per-agent J values
        infos = []
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

            M = info["M_es"]            # (N,)
            D = info["D_es"]            # (N,)
            omega = info["omega"]       # (N,) p.u.
            omega_dot = info["omega_dot"]
            P_es = info["P_es"]         # electrical (Pe)
            # Pm via GENCLS tm/Pm (only at vsg_idx positions)
            pm_full = np.asarray(getattr(ss.GENCLS, pm_attr).v).copy()
            Pm = np.array([
                pm_full[list(ss.GENCLS.idx.v).index(env.vsg_idx[i])]
                for i in range(env.N_AGENTS)
            ])

            # Swing eq residual per agent: M·ω̇ + D·(ω-1) - (Pm - Pe)
            r_phys = M * omega_dot + D * (omega - 1.0) - (Pm - P_es)
            residuals.append(r_phys.tolist())
            infos.append({"t": info["time"], "max_df": info["max_freq_deviation_hz"]})
            if done:
                break

        env.close()
        residuals = np.array(residuals)  # (T, N)
        if residuals.size == 0:
            out["computable"] = False
            out["verdict"] = "INFEASIBLE — no steps completed"
            _save(out)
            return 0

        out["computable"] = True
        out["n_steps"] = int(residuals.shape[0])
        out["n_agents"] = int(residuals.shape[1])
        # Per-step squared L2 across agents (matches J_physics scalar form)
        J_per_step = (residuals ** 2).sum(axis=1)  # (T,)
        out["J_per_step_first_5"] = J_per_step[:5].tolist()
        out["J_median"] = float(np.median(J_per_step))
        out["J_mean"] = float(np.mean(J_per_step))
        out["J_max"] = float(np.max(J_per_step))
        out["J_min"] = float(np.min(J_per_step))
        out["residual_per_agent_mean"] = residuals.mean(axis=0).tolist()
        out["residual_per_agent_max_abs"] = np.abs(residuals).max(axis=0).tolist()
        out["any_nan"] = bool(np.isnan(residuals).any())
        out["any_inf"] = bool(np.isinf(residuals).any())

        # Verdict
        med = out["J_median"]
        if out["any_nan"] or out["any_inf"]:
            out["verdict"] = "INFEASIBLE — NaN/inf in residual (numerical instability)"
        elif med > 1.0:
            out["verdict"] = f"MARGINAL — J_median={med:.3e} > 1, λ 难选 (太敏感于 SAC 探索)"
        elif med < 1e-6:
            out["verdict"] = f"WEAK — J_median={med:.3e} < 1e-6, signal 几乎为 0, 正则项无效"
        else:
            lam_est = 1.0 / max(med, 1e-12)
            out["verdict"] = (
                f"FEASIBLE — J_median={med:.3e} sys_pu², "
                f"建议 λ ≈ {lam_est:.2e} (使 λ·J ≈ O(1) 跟 critic Q 量级匹配)"
            )

        print("=== R11 PI-AC residual MVV ===")
        print(f"  pm_attr used         : {pm_attr}")
        print(f"  steps                : {out['n_steps']}")
        print(f"  J_min/median/max     : {out['J_min']:.3e} / {out['J_median']:.3e} / {out['J_max']:.3e}")
        print(f"  any nan/inf          : {out['any_nan']}/{out['any_inf']}")
        print(f"  per-agent mean res   : {[f'{x:.3e}' for x in out['residual_per_agent_mean']]}")
        print(f"  verdict              : {out['verdict']}")
    except Exception as e:
        out["error"] = str(e)[:200]
        out["traceback"] = traceback.format_exc()[:500]
        print(f"R11 ERROR: {out['error']}")

    _save(out)
    return 0


def _save(out: dict) -> None:
    p = ROOT / "results" / "research_loop" / "r11_pi_ac_residual_probe.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved: {p}")


if __name__ == "__main__":
    sys.exit(main())
