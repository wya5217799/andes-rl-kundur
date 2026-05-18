"""V4 batch DDIC eval — load every V4 trained seed, eval LS1+LS2, compute
canonical dual-eval (paper §IV-C cum_rf + 11-axis geo), rank by 6-axis geo.

Auto-discovers ckpt dirs matching `results/v4_*_s{seed}/` pattern (must contain
agent_{0..3}_best.pt OR agent_{0..3}_final.pt).

R78: ranking switched from `max_df / paper_ratio` (frequency peak only)
to the canonical 6-axis `geo` (eleven-axis paper_grade_axes). Each row
carries both paper-metric ``cum_rf`` and the 6-axis ``geo`` so callers
can re-sort by either. ``max_df`` is kept as a sanity-check column.

Output:
  results/research_loop/eval_v4_baseline/
    ddic_v4_<variant>_s<seed>_load_step_{1,2}.json
    eval_v4_summary.json   ← ranking by 6-axis geo (descending)
"""
from __future__ import annotations

import json
import re
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

STEPS = 150  # 30s @ DT=0.6 (matches eval_ddic.py)
EVAL_SEED = 42  # Matches eval_ddic.py / score_run.py default.

EVAL_OUT_DIR = ROOT / "results" / "research_loop" / "eval_v4_baseline"
RESULTS_DIR = ROOT / "results"

# pattern: results/v4_<variant>_s<seed>/  with agent_*_best.pt
CKPT_DIR_PATTERN = re.compile(r"^v4_(\S+)_s(\d+)$")


def find_v4_ckpt_dirs() -> list[tuple[str, int, Path]]:
    """Find all V4 checkpoint dirs. Returns (variant, seed, dir)."""
    found = []
    for p in RESULTS_DIR.iterdir():
        if not p.is_dir():
            continue
        m = CKPT_DIR_PATTERN.match(p.name)
        if not m:
            continue
        variant = m.group(1)
        seed = int(m.group(2))
        # Check at least one best ckpt exists
        if not (p / "agent_0_best.pt").exists() and not (p / "agent_0_final.pt").exists():
            continue
        found.append((variant, seed, p))
    return sorted(found, key=lambda r: (r[0], r[1]))


def eval_one(variant: str, seed: int, ckpt_dir: Path) -> dict:
    label = f"ddic_v4_{variant}_s{seed}"
    suffix = "best" if (ckpt_dir / "agent_0_best.pt").exists() else "final"
    print(f"\n--- {label} (suffix={suffix}) ---")
    out: dict = {"variant": variant, "seed": seed, "ckpt_dir": str(ckpt_dir),
                 "suffix": suffix, "label": label, "results": {}, "summary": None}
    try:
        agents = load_agents(ckpt_dir, suffix=suffix)
    except Exception as e:
        out["error"] = f"load_agents: {str(e)[:200]}"
        return out
    action_fn = deterministic_actor_action_fn(agents)

    trace_paths: dict[str, Path] = {}
    for scen, du in SCENARIOS.items():
        try:
            rep = run_scenario(
                scen, du,
                action_fn=action_fn,
                label=label,
                seed=EVAL_SEED,
                steps=STEPS,
            )
            trace_path = EVAL_OUT_DIR / f"{label}_{scen}.json"
            trace_path.write_text(
                json.dumps(rep, indent=2, default=str), encoding="utf-8"
            )
            trace_paths[scen] = trace_path
            out["results"][scen] = {
                "max_df": rep["max_df"],
                "cum_rf_total_local": rep["cum_rf_total"],  # local r_f (not paper §IV-C)
                "n_steps": rep["n_steps"],
            }
            print(f"  {scen}: max_df={rep['max_df']:.3f} n_steps={rep['n_steps']}")
        except Exception as e:
            out["results"][scen] = {"error": str(e)[:200],
                                    "trace": traceback.format_exc()[:500]}
            print(f"  {scen} ERR: {str(e)[:100]}")

    # R78: dual-eval (paper §IV-C cum_rf + 11-axis geo) via canonical helper.
    if trace_paths:
        try:
            out["summary"] = score_trace_files(trace_paths, label=label, is_ddic=True)
            s = out["summary"]
            print(
                f"  -> geo={s['geo']:.4f}  cum_rf={s['cum_rf']:.4f}"
                if s.get("geo") is not None else "  -> dual-eval skipped (no traces)"
            )
        except Exception as e:
            out["summary_error"] = str(e)[:200]
            print(f"  dual-eval ERR: {str(e)[:100]}")
    return out


def main() -> int:
    EVAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"=== V4 batch eval (out -> {EVAL_OUT_DIR}) ===\n")

    dirs = find_v4_ckpt_dirs()
    if not dirs:
        print("No V4 ckpt dirs found (pattern: results/v4_*_s<seed>/agent_0_{best,final}.pt)")
        return 1
    print(f"Found {len(dirs)} V4 ckpt dirs:")
    for v, s, _ in dirs:
        print(f"  {v}_s{s}")

    summary = []
    for variant, seed, ckpt_dir in dirs:
        out = eval_one(variant, seed, ckpt_dir)
        summary.append(out)

    # R78: rank by canonical 6-axis geo (descending). Keep max_df for sanity-check.
    rank_rows = []
    for s in summary:
        smry = s.get("summary") or {}
        if smry.get("geo") is None:
            continue
        ls1_max_df = s["results"].get("load_step_1", {}).get("max_df")
        ls2_max_df = s["results"].get("load_step_2", {}).get("max_df")
        rank_rows.append({
            "label": s["label"],
            "variant": s["variant"],
            "seed": s["seed"],
            "geo": smry["geo"],
            "LS1_geo": smry["LS1"],
            "LS2_geo": smry["LS2"],
            "cum_rf": smry["cum_rf"],
            "cum_rf_LS1": smry["cum_rf_LS1"],
            "cum_rf_LS2": smry["cum_rf_LS2"],
            "ls1_max_df": ls1_max_df,
            "ls2_max_df": ls2_max_df,
        })
    rank_rows.sort(key=lambda r: -r["geo"])

    summary_path = EVAL_OUT_DIR / "eval_v4_summary.json"
    summary_path.write_text(
        json.dumps({"detail": summary, "ranking": rank_rows}, indent=2, default=str),
        encoding="utf-8",
    )
    print("\n=== Ranking by 6-axis geo (higher = better) ===")
    print(f"{'rank':<5}{'label':<40}{'geo':>8}{'cum_rf':>10}"
          f"{'LS1 max_df':>12}{'LS2 max_df':>12}")
    for i, r in enumerate(rank_rows, 1):
        print(
            f"{i:<5}{r['label']:<40}{r['geo']:>8.4f}{r['cum_rf']:>10.3f}"
            f"{(r['ls1_max_df'] or 0.0):>12.3f}{(r['ls2_max_df'] or 0.0):>12.3f}"
        )
    print(f"\nSaved: {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
