"""R51 — score SAC h=64 norm 3-seed sweep + diagnostic (util / span / corr).

Mirrors the inline scoring pattern from R48/R49/R50 but adapted for SAC
ckpts (auto-detected by checkpoint_loader.load_agents). Outputs JSON
with both 6-axis scores and the diagnostic metrics that distinguish
"stochastic-policy temporal variation" from "static-setpoint policy".

Run: /home/wya/andes_venv/bin/python scripts/_r51_score_sac_h64.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_grade_axes import (  # noqa: E402
    PAPER,
    evaluate_trace,
)
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
SEEDS = (49, 50, 51)
HIDDEN = (64, 64, 64, 64)


def main() -> None:
    rows = []
    for seed in SEEDS:
        ckpt = ROOT / "results" / f"sac_norm_h64_s{seed}"
        label = f"sac_norm_h64_s{seed}"
        agents = load_agents(ckpt, suffix="best", hidden_sizes=HIDDEN)
        afn = deterministic_actor_action_fn(agents)
        per: dict[str, float] = {}
        util = {"dH": [], "dD": []}
        smooth = {"dH": [], "dD": []}
        settling: list[float] = []
        max_df_score: list[float] = []
        span_pct = {"dM": [], "dD": []}
        corr = {"dM": [], "dD": []}
        for scen, du in SCENARIOS.items():
            rec = run_scenario(scen, du, action_fn=afn, label=label, seed=42, steps=150)
            (EVAL_OUT / f"{label}_{scen}.json").write_text(
                json.dumps(rec), encoding="utf-8"
            )
            ts = evaluate_trace(
                EVAL_OUT / f"{label}_{scen}.json", PAPER[scen], is_ddic=True, label=label
            )
            per[scen] = ts.overall
            for ax in ts.axes:
                if ax.name == "dH_utilization":
                    util["dH"].append(ax.score)
                elif ax.name == "dD_utilization":
                    util["dD"].append(ax.score)
                elif ax.name == "dH_smoothness":
                    smooth["dH"].append(ax.score)
                elif ax.name == "dD_smoothness":
                    smooth["dD"].append(ax.score)
                elif ax.name == "settling_s":
                    settling.append(ax.score)
                elif ax.name == "max_|df|_Hz":
                    max_df_score.append(ax.score)
            t_arr = np.array([s["t"] for s in rec["traces"]])
            mask = t_arr <= t_arr[0] + 6.0
            dM = np.array([s["delta_M"] for s in rec["traces"]])[mask]
            dD = np.array([s["delta_D"] for s in rec["traces"]])[mask]
            span_pct["dM"].append((dM.max(axis=0) - dM.min(axis=0)).mean() / 400 * 100)
            span_pct["dD"].append((dD.max(axis=0) - dD.min(axis=0)).mean() / 800 * 100)
            cM = np.corrcoef(dM.T)
            cD = np.corrcoef(dD.T)
            mk = ~np.eye(4, dtype=bool)
            corr["dM"].append(cM[mk].mean())
            corr["dD"].append(cD[mk].mean())
        geo = math.exp(
            sum(math.log(max(x, 0.01)) for x in per.values()) / len(per)
        )
        rows.append(
            {
                "seed": seed,
                "LS1": per["load_step_1"],
                "LS2": per["load_step_2"],
                "geo": geo,
                "max_df_score": sum(max_df_score) / 2,
                "settling": sum(settling) / 2,
                "dH_util": sum(util["dH"]) / 2,
                "dD_util": sum(util["dD"]) / 2,
                "dH_smooth": sum(smooth["dH"]) / 2,
                "dD_smooth": sum(smooth["dD"]) / 2,
                "dM_span_pct": sum(span_pct["dM"]) / 2,
                "dD_span_pct": sum(span_pct["dD"]) / 2,
                "corr_dM": sum(corr["dM"]) / 2,
                "corr_dD": sum(corr["dD"]) / 2,
            }
        )
        r = rows[-1]
        print(
            f's{seed}: LS1={r["LS1"]:.3f} LS2={r["LS2"]:.3f} geo={r["geo"]:.3f} | '
            f'max_df={r["max_df_score"]:.2f} settle={r["settling"]:.2f} '
            f'dH_u={r["dH_util"]:.3f} dD_u={r["dD_util"]:.3f} | '
            f'dM_sp%={r["dM_span_pct"]:.1f} dD_sp%={r["dD_span_pct"]:.1f}'
        )

    sc = [r["geo"] for r in rows]
    util_d_mean = sum(r["dD_util"] for r in rows) / len(rows)
    util_h_mean = sum(r["dH_util"] for r in rows) / len(rows)
    span_d = sum(r["dD_span_pct"] for r in rows) / len(rows)
    span_m = sum(r["dM_span_pct"] for r in rows) / len(rows)

    print()
    print("=== R51-α SAC norm h=64 3-seed sweep ===")
    print(
        f"  6-axis: mean={sum(sc) / len(sc):.4f}  range=[{min(sc):.4f}, {max(sc):.4f}]"
    )
    print()
    print("Reference points:")
    print(f"  R48-β TD3 norm h=64 (current production):  0.334  dD_util~0.10 dD_sp~12%")
    print(f"  R49-α TD3 norm h=64 R03 obs (FAILED):      0.263  dD_util~0.03 dD_sp~4.6%")
    print(f"  R50-α TD3 norm h=64 LAMBDA=-100 (FAILED):  0.110  dD_util~0.00 dD_sp~0.3%")
    print(f"  CLM-0048 SAC norm h=128 (R43-α):           0.117  (current SAC attractor)")
    print()
    print(f"  R51-α: dH_util_mean={util_h_mean:.3f} dD_util_mean={util_d_mean:.3f}")
    print(f"  R51-α: dM_span_mean={span_m:.1f}% dD_span_mean={span_d:.1f}%")

    out = ROOT / "results" / "research_loop" / "r51_alpha_sac_h64.json"
    out.write_text(
        json.dumps(
            {
                "r51_alpha": rows,
                "hidden_sizes": list(HIDDEN),
                "algo": "sac",
                "lambda_smooth": 0,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
