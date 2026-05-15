"""F3 — fresh-seed HAWE eval driver.

After B-2 fresh-seed training (N2; seeds 50/51/52) finishes, run HAWE
ensembles of R21 + each fresh-seed actor at the headline weight 98/2,
plus single-actor eval for each fresh seed alone, to populate the
panel-critique decisive row "is the HAWE result truly reproducible
on a non-lineage actor?"

For each fresh seed s ∈ {50, 51, 52}:
  - Eval the s alone (no ensemble) -> tests whether fresh seed alone
    is anywhere near R21's 0.444
  - Eval HAWE 98/2 = 0.98·R21 + 0.02·s -> tests whether HAWE recovery
    works without lineage (ws8 is R21-derivative; sN are not)

Run (WSL, after N2 finishes — verify each
``results/v4_h50_s{50,51,52}/agent_3_best.pt`` exists):

    /home/wya/andes_venv/bin/python scripts/research_loop/eval_n2_fresh_seed_hawe.py

Outputs:
    results/research_loop/eval_v4_baseline/ddic_v4_h50_s{50,51,52}_load_step_{1,2}.json
    results/research_loop/eval_v4_baseline/ddic_v4_ens_R21_freshs{50,51,52}_w9802_load_step_{1,2}.json
    results/research_loop/r32_n2_fresh_seed_manifest.json
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
EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"
PYTHON = "/home/wya/andes_venv/bin/python"


def fresh_dir(seed: int) -> Path:
    return ROOT / "results" / f"v4_h50_s{seed}"


def all_ckpts_present(d: Path, suffix: str = "best") -> bool:
    return all((d / f"agent_{i}_{suffix}.pt").exists() for i in range(4))


def run_single(seed: int) -> int:
    """Single-actor eval of one fresh seed."""
    d = fresh_dir(seed)
    label = f"ddic_v4_h50_s{seed}"
    cmd = [
        PYTHON,
        str(ROOT / "scripts" / "research_loop" / "eval_v4_ddic.py"),
        "--ckpt-dir", str(d.relative_to(ROOT)),
        "--suffix", "best",
        "--label", label,
        "--out-dir", str(EVAL_OUT.relative_to(ROOT)),
    ]
    print(f"[F3] single -> {label}", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def run_hawe(seed: int, weight_r21: float = 0.98) -> int:
    """HAWE 2-actor (R21 + fresh seed) eval at weight w_R21."""
    d = fresh_dir(seed)
    w_str = f"{int(round(weight_r21 * 100)):02d}{int(round((1 - weight_r21) * 100)):02d}"
    label = f"ddic_v4_ens_R21_freshs{seed}_w{w_str}"
    cmd = [
        PYTHON,
        str(ROOT / "scripts" / "research_loop" / "eval_v4_ensemble.py"),
        "--ckpt-dirs", str(R21_DIR.relative_to(ROOT)), str(d.relative_to(ROOT)),
        "--suffixes", "best", "best",
        "--weights", str(weight_r21), str(1.0 - weight_r21),
        "--agg", "weighted",
        "--label", label,
        "--out-dir", str(EVAL_OUT.relative_to(ROOT)),
    ]
    print(f"[F3] HAWE -> {label}", flush=True)
    return subprocess.run(cmd, cwd=ROOT).returncode


def main() -> int:
    EVAL_OUT.mkdir(parents=True, exist_ok=True)

    # Pre-flight: verify each fresh seed has best ckpts.
    missing: list[int] = []
    for s in FRESH_SEEDS:
        if not all_ckpts_present(fresh_dir(s)):
            missing.append(s)
    if missing:
        print(f"[F3] PRE-FLIGHT FAIL — fresh seeds missing best.pt: {missing}",
              flush=True)
        print(f"[F3] wait for N2 training to finish on those seeds first.",
              flush=True)
        return 2

    summaries: list[dict] = []
    for seed in FRESH_SEEDS:
        t0 = time.time()
        rc_single = run_single(seed)
        rc_hawe = run_hawe(seed, weight_r21=0.98)
        dt = time.time() - t0
        summaries.append({
            "seed": seed,
            "single_rc": rc_single,
            "hawe_rc": rc_hawe,
            "wall_s": dt,
        })

    manifest = {
        "generated_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fresh_seeds": list(FRESH_SEEDS),
        "headline_weight": 0.98,
        "summaries": summaries,
        "next_action": (
            "Run `python scripts/research_loop/dump_eval_v4_ranking.py` to "
            "see where the new entries land in the post-fix ranking."
        ),
    }
    out = ROOT / "results" / "research_loop" / "r32_n2_fresh_seed_manifest.json"
    out.write_text(json.dumps(manifest, indent=2))
    print(f"\n[F3] manifest -> {out.relative_to(ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
