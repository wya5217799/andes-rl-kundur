"""R106-W1 (D4): Env stochasticity floor — disturbance-magnitude stress envelope.

R84 plan §D4 axis: "Does eval geo vary substantially under env-side
variance, such that 0.391 is a noise ceiling rather than a policy
ceiling?" The cleanest meaningful 'env variance' is **disturbance
magnitude**: real grids see load steps of different sizes, and the
paper-cited LS1 (-2.48 pu @ Bus 14) / LS2 (+1.88 pu @ Bus 15) are one
operating point.

Run R72_w4 SOTA × magnitude_scale ∈ {0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0}
× both scenarios = 14 ANDES evals. Score each via canonical
`score_trace_files`. Report:

- geo distribution mean / median / IQR across scales
- σ_geo / mean_geo (coefficient of variation)
- Per-scale geo curve (does it monotone-decay with disturbance size?)

If σ_geo / mean_geo ≥ 0.30 → 0.391 is a noise ceiling; disturbance
randomization explains a lot of the plateau interpretation.
If ≤ 0.15 → SOTA is robust to magnitude; 0.391 is a real policy
ceiling.

Zero training. 1 WSL slot during the 14-eval burst (~3.5 min).

Output: `results/r106_d4_env_floor/{summary.json, magnitude_curve.csv}`

Usage (WSL):
    source ~/andes_venv/bin/activate
    cd /mnt/c/Users/27443/Desktop/andes-rl-kundur
    python3 scripts/r106_d4_env_floor.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.agents.checkpoint_loader import load_agents  # noqa: E402
from andes_rl_kundur.evaluation.paper_path import (  # noqa: E402
    deterministic_actor_action_fn,
    run_scenario,
)
from andes_rl_kundur.evaluation.summary import score_trace_files  # noqa: E402
from andes_rl_kundur.probes.andes_common.paper_constants import (  # noqa: E402
    LS1_DELTA_U,
    LS2_DELTA_U,
    LS1_NAME,
    LS2_NAME,
)

# ─── Config ───────────────────────────────────────────────────────────
SOTA_DIR = ROOT / "results" / "r72_w4_lstm_tau001_warmup5_s54"
OUT_DIR = ROOT / "results" / "r106_d4_env_floor"
ENV_SEED = 42
STEPS = 150  # canonical 30s window — same as eval_ddic.py
MAGNITUDES = [0.50, 0.75, 1.00, 1.25, 1.50, 1.75, 2.00]
SCEN_BASE = {LS1_NAME: LS1_DELTA_U, LS2_NAME: LS2_DELTA_U}


def scale_delta_u(base: dict, factor: float) -> dict:
    return {k: v * factor for k, v in base.items()}


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    print(f"[R106-D4] Loading SOTA: {SOTA_DIR}")
    agents = load_agents(SOTA_DIR, suffix="best")
    print(f"[R106-D4] {len(agents)} agents loaded")

    per_scale: list[dict] = []
    trace_dir_root = OUT_DIR / "traces"
    trace_dir_root.mkdir(exist_ok=True)

    for factor in MAGNITUDES:
        scale_dir = trace_dir_root / f"scale_{int(factor*100):03d}"
        scale_dir.mkdir(exist_ok=True)
        t_s = time.time()
        trace_paths: dict[str, Path] = {}
        scen_meta = {}
        any_failed = False
        for scen_name, base in SCEN_BASE.items():
            delta_u = scale_delta_u(base, factor)
            action_fn = deterministic_actor_action_fn(agents)
            label = f"r106_scale{int(factor*100):03d}"
            rec = run_scenario(
                scen_name, delta_u,
                action_fn=action_fn,
                label=label,
                seed=ENV_SEED,
                steps=STEPS,
            )
            scen_meta[scen_name] = {
                "delta_u_applied": delta_u,
                "n_steps": rec.get("n_steps"),
                "max_df": rec.get("max_df"),
                "cum_rf_total": rec.get("cum_rf_total"),
            }
            if rec.get("n_steps", 0) < STEPS - 1:
                any_failed = True
            trace_path = scale_dir / f"trace_{scen_name}.json"
            trace_path.write_text(json.dumps(rec, indent=2))
            trace_paths[scen_name] = trace_path

        scored = score_trace_files(trace_paths, label=f"r106_scale_{int(factor*100):03d}", is_ddic=True)
        wall = time.time() - t_s
        print(f"  scale={factor:.2f}: geo={scored.get('geo'):.4f} LS1={scored.get('LS1'):.4f} "
              f"LS2={scored.get('LS2'):.4f} cum_rf={scored.get('cum_rf'):.4f} "
              f"any_failed={any_failed}  wall={wall:.1f}s")

        per_scale.append({
            "magnitude_scale": factor,
            "scen_meta": scen_meta,
            "any_failed": any_failed,
            **scored,
        })

    # Aggregate stats
    valid = [p for p in per_scale if p.get("geo") is not None and not p["any_failed"]]
    if not valid:
        print("FATAL: no valid scales")
        return 1

    geos = np.array([p["geo"] for p in valid])
    ls1s = np.array([p["LS1"] for p in valid])
    ls2s = np.array([p["LS2"] for p in valid])
    cum_rfs = np.array([p["cum_rf"] for p in valid])

    # Center magnitude (1.0) for reference
    center = next((p for p in valid if p["magnitude_scale"] == 1.0), None)

    cv_geo = float(geos.std() / max(abs(geos.mean()), 1e-9))

    # Verdict gate
    if cv_geo > 0.30:
        gate = "ENV_FLOOR_HIGH_DOMINATES_PLATEAU"
        interp = (
            f"σ_geo / mean_geo = {cv_geo:.2f} > 0.30 — SOTA's 6-axis varies by "
            f"more than 30% across legitimate disturbance magnitudes. The 0.391 "
            f"baseline is partly a noise ceiling, not a pure policy ceiling. "
            f"R107+ must report eval distributions, not single-magnitude headline."
        )
    elif cv_geo > 0.15:
        gate = "ENV_FLOOR_MODERATE_REPORT_AS_RANGE"
        interp = (
            f"σ_geo / mean_geo = {cv_geo:.2f} ∈ (0.15, 0.30] — moderate env "
            f"variance. Eval methodology should report multi-magnitude range, "
            f"but 0.391 is still meaningful as a representative number."
        )
    else:
        gate = "POLICY_CEILING_NOT_ENV_FLOOR"
        interp = (
            f"σ_geo / mean_geo = {cv_geo:.2f} ≤ 0.15 — SOTA's 6-axis is robust "
            f"to disturbance magnitude variation. 0.391 is a real policy "
            f"ceiling, not a noise floor."
        )

    summary = {
        "round": "R106",
        "wave": "W1_D4_env_floor",
        "title": "Disturbance-magnitude stress envelope for R72_w4 SOTA",
        "sota": str(SOTA_DIR.relative_to(ROOT)),
        "suffix": "best",
        "magnitudes": MAGNITUDES,
        "env_seed": ENV_SEED,
        "steps": STEPS,
        "per_scale": per_scale,
        "geo_distribution": {
            "n": len(geos),
            "mean": float(geos.mean()),
            "median": float(np.median(geos)),
            "std": float(geos.std()),
            "p10": float(np.percentile(geos, 10)),
            "p90": float(np.percentile(geos, 90)),
            "min": float(geos.min()),
            "max": float(geos.max()),
            "range": float(geos.max() - geos.min()),
            "cv": cv_geo,
        },
        "ls1_distribution": {
            "mean": float(ls1s.mean()), "std": float(ls1s.std()),
            "min": float(ls1s.min()), "max": float(ls1s.max()),
        },
        "ls2_distribution": {
            "mean": float(ls2s.mean()), "std": float(ls2s.std()),
            "min": float(ls2s.min()), "max": float(ls2s.max()),
        },
        "cum_rf_distribution": {
            "mean": float(cum_rfs.mean()), "std": float(cum_rfs.std()),
            "min": float(cum_rfs.min()), "max": float(cum_rfs.max()),
        },
        "reference_center": center,
        "verdict": {
            "gate": gate,
            "interpretation": interp,
            "cv_geo": cv_geo,
        },
        "wall_seconds": time.time() - t0,
    }

    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

    print(f"\n[R106-D4] ─── VERDICT ───")
    print(f"  gate: {gate}")
    print(f"  {interp}\n")
    print(f"  geo distribution: mean={geos.mean():.4f}  median={np.median(geos):.4f}  "
          f"σ={geos.std():.4f}  range [{geos.min():.4f}, {geos.max():.4f}]  cv={cv_geo:.3f}")
    print(f"  cum_rf  mean = {cum_rfs.mean():+.4f}  range [{cum_rfs.min():+.4f}, {cum_rfs.max():+.4f}]")
    print(f"\n  Per-scale geo:")
    for p in per_scale:
        f = p['magnitude_scale']
        g = p.get('geo') if p.get('geo') is not None else float('nan')
        fail_tag = " (TDS_FAILED)" if p['any_failed'] else ""
        print(f"    scale={f:.2f}  geo={g:.4f}{fail_tag}")
    print(f"\n  written: {OUT_DIR / 'summary.json'}  wall: {summary['wall_seconds']:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
