"""R113 — Toggler-Line_8 ablation (Q-0025 A1).

CLM-0194 (R110 audit): V4 env ships with ANDES default `Toggler` trip on
`Line_8` (Area 2 internal) at t=2.0 s, which V4 env never disables. Every
R57-R85 LS1/LS2 scenario is therefore a *compound* disturbance (paper load
step at t=0.5 s + line trip at t=2 s).

R113 runs the cheapest possible falsification:

    V4 env × zero-action × LS1+LS2 × {Toggler u=1 (default), Toggler u=0}

4 ANDES TDS evals. Reports max_df, cum_rf, 11-axis geo for both toggler
states and the drop magnitude.

Decision rules (per Q-0025):
    max_df drop ≥ 30%  → Toggler dominant, R114 re-baseline
    max_df drop 10-30% → meaningful but not dominant
    max_df drop < 10%  → minor; Q-0025 closed-negative

Run (WSL only — CLAUDE.md ANDES rule):
    /home/wya/andes_venv/bin/python scripts/r113_toggler_ablation.py
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.andes_vsg_env_v4 import AndesMultiVSGEnvV4  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import zero_action_fn  # noqa: E402
from andes_rl_kundur.evaluation.summary import (  # noqa: E402
    format_headline,
    score_trace_files,
)
from andes_rl_kundur.probes.andes_common.paper_constants import SCENARIOS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("r113")

OUT_DIR = ROOT / "results" / "r113_toggler_ablation"
OUT_DIR.mkdir(parents=True, exist_ok=True)

STEPS = 150          # paper-cited; matches R85/R80 cross-eval setup
SEED = 42            # paper seed
DT_NOMINAL = 0.2     # KUNDUR_4VSG.dt, RL control step


def _toggler_state(env: AndesMultiVSGEnvV4) -> dict[str, Any]:
    """Snapshot Toggler entries for logging / sanity."""
    if not hasattr(env.ss, "Toggler"):
        return {"n": 0, "u": []}
    return {
        "n": int(env.ss.Toggler.n),
        "u": [float(x) for x in env.ss.Toggler.u.v],
        "t": [float(x) for x in env.ss.Toggler.t.v] if hasattr(env.ss.Toggler, "t") else [],
        "dev": list(env.ss.Toggler.dev.v) if hasattr(env.ss.Toggler, "dev") else [],
    }


def run_scenario_with_toggler(
    scen_name: str,
    delta_u: dict[str, Any],
    toggler_u: float,
    *,
    label: str,
    seed: int = SEED,
    steps: int = STEPS,
) -> dict[str, Any]:
    """Run zero-action LS1/LS2 with explicit Toggler u override.

    Patch site: post-`env.reset` (which has already run warmup to t=0.5 +
    applied disturbance, both before Toggler.t=2.0 fires), set
    `env.ss.Toggler.u.v[:] = toggler_u` before the step loop.

    Returns a trace dict in the same shape as `paper_path.run_scenario`,
    plus `toggler_u` and `toggler_state_pre_step` fields for audit.
    """
    env = AndesMultiVSGEnvV4(random_disturbance=False, comm_fail_prob=0.0)
    traces: list[dict[str, Any]] = []
    cum_rf = 0.0
    max_df = 0.0
    osc_accum = 0.0
    try:
        env.seed(seed)
        env.STEPS_PER_EPISODE = steps
        obs = env.reset(delta_u=delta_u)

        # R113 — Toggler u override (post-reset, pre-step). The reset()
        # warmup runs TDS to t=0.5; Toggler.t=2.0 has not yet fired.
        # Setting u=0 disables it for the upcoming step loop.
        pre_state = _toggler_state(env)
        if hasattr(env.ss, "Toggler") and env.ss.Toggler.n > 0:
            env.ss.Toggler.u.v[:] = float(toggler_u)
        post_state = _toggler_state(env)
        log.info(
            f"  [{label}/{scen_name}] toggler_u set to {toggler_u}; "
            f"pre={pre_state}; post.u={post_state['u']}"
        )

        n_agents = env.N_AGENTS
        f_nom = env.FN

        for step in range(steps):
            actions = zero_action_fn(step, obs, n_agents)
            obs, _rewards, done, info = env.step(actions)
            if info.get("tds_failed"):
                break

            freq_hz = info["freq_hz"].astype(float).tolist()
            delta_f = [(f - f_nom) for f in freq_hz]
            f_bar = float(np.mean(freq_hz))
            step_rf = float(
                np.mean([(d - (f_bar - f_nom)) ** 2 for d in delta_f])
            )
            cum_rf -= step_rf
            max_df = max(max_df, float(np.max(np.abs(delta_f))))
            osc_accum += float(np.std(delta_f))

            traces.append({
                "step":       step,
                "t":          float(info["time"]),
                "freq_hz":    freq_hz,
                "f_bar":      f_bar,
                "step_rf":    step_rf,
                "delta_P_es": info["P_es"].astype(float).tolist(),
                "delta_f_es": delta_f,
                "M_es":       info["M_es"].astype(float).tolist(),
                "D_es":       info["D_es"].astype(float).tolist(),
                "delta_M":    info["delta_M"].astype(float).tolist(),
                "delta_D":    info["delta_D"].astype(float).tolist(),
            })
            if done:
                break
    finally:
        env.close()

    return {
        "controller":         label,
        "scenario":           scen_name,
        "env_version":        "v4",
        "toggler_u":          float(toggler_u),
        "toggler_state_pre":  pre_state,
        "toggler_state_post": post_state,
        "cum_rf_total":       cum_rf,
        "max_df":             max_df,
        "osc":                osc_accum,
        "n_steps":            len(traces),
        "traces":             traces,
    }


def main() -> None:
    log.info(f"R113 toggler ablation → {OUT_DIR}")
    t_start = time.time()

    # 1. Run all 4 (toggler × scenario) combinations
    trace_paths: dict[str, dict[str, Path]] = {}  # state → {scen → path}
    summaries: dict[str, Any] = {}
    for toggler_u in (1.0, 0.0):
        state_tag = f"u{int(toggler_u)}"
        scen_paths: dict[str, Path] = {}
        log.info(f"\n=== Toggler u={int(toggler_u)} "
                 f"({'default/with-trip' if toggler_u else 'disabled/no-trip'}) ===")
        for scen, du in SCENARIOS.items():
            rep = run_scenario_with_toggler(
                scen, du, toggler_u, label=f"toggler_{state_tag}",
                seed=SEED, steps=STEPS,
            )
            p = OUT_DIR / f"toggler_{state_tag}_{scen}.json"
            p.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
            scen_paths[scen] = p
            log.info(
                f"  toggler_{state_tag}/{scen}: "
                f"max_df={rep['max_df']:.4f} cum_rf={rep['cum_rf_total']:.4f} "
                f"n_steps={rep['n_steps']}"
            )
        trace_paths[state_tag] = scen_paths

    # 2. The "no_control" reference for axis 8 is the toggler-default trace
    # (since paper-cited numbers were computed against that default env).
    # Copy the u=1 traces as no_control sibling for axis 8.
    nc_dir = OUT_DIR / "_no_control_cache"
    nc_dir.mkdir(parents=True, exist_ok=True)
    for scen in SCENARIOS:
        nc_path = nc_dir / f"no_control_{scen}.json"
        if not nc_path.exists():
            # Re-label u=1 trace as no_control (it IS zero-action)
            src = trace_paths["u1"][scen]
            data = json.loads(src.read_text(encoding="utf-8"))
            data["controller"] = "no_control"
            nc_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # 3. Score each toggler state with sibling no_control refs
    import shutil
    for state_tag in ("u1", "u0"):
        sub_dir = OUT_DIR / f"score_{state_tag}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        score_paths: dict[str, Path] = {}
        for scen in SCENARIOS:
            # copy controller trace
            dst = sub_dir / f"toggler_{state_tag}_{scen}.json"
            if not dst.exists():
                shutil.copy(trace_paths[state_tag][scen], dst)
            score_paths[scen] = dst
            # copy no_control reference (axis-8 sibling)
            nc_dst = sub_dir / f"no_control_{scen}.json"
            if not nc_dst.exists():
                shutil.copy(nc_dir / f"no_control_{scen}.json", nc_dst)
        summary = score_trace_files(
            score_paths, label=f"toggler_{state_tag}", is_ddic=False,
        )
        summaries[state_tag] = summary
        log.info(f"\n  toggler_{state_tag} summary: {format_headline(summary)}")

    # 4. Headline + decision rule
    # max_df per (toggler_state × scen)
    max_df = {
        state_tag: {
            scen: json.loads(trace_paths[state_tag][scen].read_text(encoding="utf-8"))["max_df"]
            for scen in SCENARIOS
        }
        for state_tag in ("u1", "u0")
    }
    # Drop fractions
    drops = {}
    for scen in SCENARIOS:
        u1 = max_df["u1"][scen]
        u0 = max_df["u0"][scen]
        drops[scen] = {
            "u1_max_df_Hz": u1,
            "u0_max_df_Hz": u0,
            "drop_abs_Hz":  u1 - u0,
            "drop_pct":     100.0 * (u1 - u0) / u1 if u1 else 0.0,
        }
        log.info(
            f"\n  {scen}: u=1 max_df={u1:.4f} Hz → u=0 max_df={u0:.4f} Hz"
            f" ({drops[scen]['drop_pct']:+.1f}% drop)"
        )

    avg_drop_pct = float(np.mean([drops[s]["drop_pct"] for s in SCENARIOS]))
    if avg_drop_pct >= 30.0:
        regime = "TOGGLER_DOMINANT (≥30% drop) — R114 re-baseline triggered"
    elif avg_drop_pct >= 10.0:
        regime = "TOGGLER_MEANINGFUL (10-30% drop) — partial paper rewrite"
    else:
        regime = "TOGGLER_MINOR (<10% drop) — Q-0025 closed-negative"

    log.info("\n" + "=" * 60)
    log.info(f"R113 HEADLINE — avg max_df drop = {avg_drop_pct:+.1f}%")
    log.info(f"  regime: {regime}")
    log.info("=" * 60)

    grand = {
        "round": 113,
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "steps": STEPS,
        "seed": SEED,
        "scenarios": list(SCENARIOS.keys()),
        "max_df": max_df,
        "drops": drops,
        "avg_drop_pct": avg_drop_pct,
        "regime": regime,
        "summary_u1": summaries.get("u1"),
        "summary_u0": summaries.get("u0"),
        "wall_s": time.time() - t_start,
    }
    (OUT_DIR / "r113_summary.json").write_text(
        json.dumps(grand, indent=2, default=str), encoding="utf-8"
    )
    log.info(f"\nWritten {OUT_DIR / 'r113_summary.json'}")
    log.info(f"Total wall = {grand['wall_s']:.1f} s")


if __name__ == "__main__":
    main()
