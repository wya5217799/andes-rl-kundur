"""r36 — Fresh-seed HAWE w-sweep (off-sweet-spot lineage independence).

Question
--------
r34 confirmed fresh-seed HAWE works at 98/2 (recovers 99.3% R21).
r26 says lineage-bound HAWE has a 1-12% advantage over SWA off-sweet-spot.
Does that off-sweet-spot HAWE niche also survive on fresh-seed actors?

Method
------
For w_R21 ∈ {0.50, 0.80, 0.90, 0.95} and fresh seed s ∈ {50, 51, 52}, run
HAWE eval R21 + s_N at weight w_R21. Total: 4 × 3 × 2 = 24 evals.

We do NOT include 0.98 (already done in r34) — only w-sweep below sweet
spot.

Run (WSL)
---------
    /home/wya/andes_venv/bin/python scripts/research_loop/eval_freshseed_hawe_sweep.py

Outputs
-------
    results/research_loop/eval_v4_baseline/ddic_v4_ens_R21_freshs{50,51,52}_w{50,80,90,95}{50,20,10,05}_load_step_{1,2}.json
    results/research_loop/r36_freshseed_hawe_sweep_manifest.json
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

R21_DIR = ROOT / "results" / "v4_h50_s49"
FRESH_SEEDS = (50, 51, 52)
WEIGHTS = (0.50, 0.80, 0.90, 0.95)
EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
PYTHON = "/home/wya/andes_venv/bin/python"


def fresh_dir(seed: int) -> Path:
    return ROOT / "results" / f"v4_h50_s{seed}"


def run_hawe(seed: int, w_r21: float) -> tuple[int, float]:
    d = fresh_dir(seed)
    w_str = (
        f"{int(round(w_r21 * 100)):02d}"
        f"{int(round((1 - w_r21) * 100)):02d}"
    )
    label = f"ddic_v4_ens_R21_freshs{seed}_w{w_str}"
    cmd = [
        PYTHON,
        str(ROOT / "scripts" / "research_loop" / "eval_v4_ensemble.py"),
        "--ckpt-dirs", str(R21_DIR.relative_to(ROOT)), str(d.relative_to(ROOT)),
        "--suffixes", "best", "best",
        "--weights", str(w_r21), str(1.0 - w_r21),
        "--agg", "weighted",
        "--label", label,
        "--out-dir", str(EVAL_OUT.relative_to(ROOT)),
    ]
    t0 = time.time()
    print(f"[r36] eval -> {label}", flush=True)
    rc = subprocess.run(cmd, cwd=ROOT).returncode
    dt = time.time() - t0
    print(f"[r36]   rc={rc}  dt={dt:.1f}s", flush=True)
    return rc, dt


def main() -> int:
    EVAL_OUT.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    t_global = time.time()
    for seed in FRESH_SEEDS:
        d = fresh_dir(seed)
        if not all((d / f"agent_{i}_best.pt").exists() for i in range(4)):
            print(f"[r36] SKIP seed {seed}: missing best.pt", flush=True)
            continue
        for w in WEIGHTS:
            rc, dt = run_hawe(seed, w)
            summaries.append({
                "seed": seed, "w_r21": float(w),
                "rc": rc, "wall_s": dt,
            })

    manifest = {
        "generated_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fresh_seeds": list(FRESH_SEEDS),
        "weights": list(WEIGHTS),
        "n_evals": len(summaries),
        "summaries": summaries,
        "total_wall_s": time.time() - t_global,
    }
    out = ROOT / "results" / "research_loop" / "r36_freshseed_hawe_sweep_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"\n[r36] manifest -> {out.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
