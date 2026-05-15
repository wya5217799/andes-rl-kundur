"""B-6 SWA / model-soup baseline — weight-space averaging vs action-space HAWE.

Question
--------
Izmailov 2018 (SWA) and Wortsman 2022 (model soups) average actor parameters
in weight space; HAWE (Yang/this paper) averages in action space at
inference. If SWA matches HAWE on the same R21 + ws8 pair, HAWE has no
unique novelty; if SWA collapses, HAWE has a real action-space niche.

This script:
  1. averages the actor state_dict of R21 + ws8 at w_R21 in {0.50, 0.80,
     0.90, 0.95, 0.98} (5 points spanning the HAWE sweep)
  2. saves merged checkpoints under ``results/v4_swa_w{50,80,90,95,98}/``
  3. runs the standard ``eval_v4_ddic.py`` driver on each merged controller
  4. invokes ``evaluation/paper_grade_axes.py`` once on the eval directory
     to rank all controllers (including pre-existing R21 / HAWE 98/2 / ws8
     traces, if present)

Per-agent: actor only is averaged (HAWE uses actor outputs); critic /
critic_target / log_alpha / optimisers are inherited from R21 so the saved
checkpoint round-trips through ``SACAgent.load`` unchanged.

Run (WSL):
    /home/wya/andes_venv/bin/python scripts/research_loop/eval_swa_baseline.py

Outputs:
    results/v4_swa_w{50,80,90,95,98}/agent_{0..3}_best.pt
    results/research_loop/eval_v4_baseline/ddic_v4_swa_w*_load_step_{1,2}.json
    results/research_loop/r26_swa_manifest.json
    quality_reports/research_loop/r26_swa_baseline_verdict.md (handwritten)
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

import torch


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

R21_DIR = ROOT / "results" / "v4_h50_s49"
WS8_DIR = ROOT / "results" / "v4_8_warmstart_R21_s49"
EVAL_OUT = ROOT / "results" / "research_loop" / "eval_v4_baseline"

WEIGHTS_DEFAULT: tuple[float, ...] = (0.50, 0.80, 0.90, 0.95, 0.98)
N_AGENTS = 4
PYTHON_DEFAULT = "/home/wya/andes_venv/bin/python"


def _label_for(w: float) -> str:
    return f"ddic_v4_swa_w{int(round(w * 100)):02d}"


def _ckpt_dir_for(w: float) -> Path:
    return ROOT / "results" / f"v4_swa_w{int(round(w * 100)):02d}"


def make_swa_ckpts(w_r21: float, *, force: bool = False) -> Path:
    """Average actor state_dict R21 + ws8 at weight w_r21 / (1-w_r21). Save."""
    out_dir = _ckpt_dir_for(w_r21)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not force:
        all_present = all(
            (out_dir / f"agent_{i}_best.pt").exists() for i in range(N_AGENTS)
        )
        if all_present:
            print(f"[swa] {out_dir.name} already populated — skipping merge", flush=True)
            return out_dir

    for i in range(N_AGENTS):
        ckpt_r21 = torch.load(R21_DIR / f"agent_{i}_best.pt",
                              map_location="cpu", weights_only=False)
        ckpt_ws8 = torch.load(WS8_DIR / f"agent_{i}_best.pt",
                              map_location="cpu", weights_only=False)
        actor_r21 = ckpt_r21["actor"]
        actor_ws8 = ckpt_ws8["actor"]
        actor_swa: OrderedDict[str, torch.Tensor] = OrderedDict()
        for key, t_r21 in actor_r21.items():
            t_ws8 = actor_ws8.get(key)
            if (
                isinstance(t_r21, torch.Tensor)
                and isinstance(t_ws8, torch.Tensor)
                and t_r21.shape == t_ws8.shape
            ):
                # Cast to float for the linear combination, restore dtype.
                blend = (
                    w_r21 * t_r21.detach().float()
                    + (1.0 - w_r21) * t_ws8.detach().float()
                ).to(t_r21.dtype)
                actor_swa[key] = blend
            else:
                # Non-tensor or shape mismatch: keep R21 (e.g. buffers).
                actor_swa[key] = t_r21

        ckpt_swa = dict(ckpt_r21)
        ckpt_swa["actor"] = actor_swa
        meta = dict(ckpt_swa.get("metadata") or {})
        meta.update({
            "swa_w_r21": float(w_r21),
            "swa_source_r21": str(R21_DIR.relative_to(ROOT)),
            "swa_source_ws8": str(WS8_DIR.relative_to(ROOT)),
            "swa_method": "weight_space_actor_only",
            "swa_generated_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        ckpt_swa["metadata"] = meta
        torch.save(ckpt_swa, out_dir / f"agent_{i}_best.pt")
    print(f"[swa] wrote {N_AGENTS} ckpts to {out_dir}", flush=True)
    return out_dir


def run_eval(ckpt_dir: Path, label: str, python_bin: str) -> int:
    cmd = [
        python_bin,
        str(ROOT / "scripts" / "research_loop" / "eval_v4_ddic.py"),
        "--ckpt-dir", str(ckpt_dir.relative_to(ROOT)),
        "--suffix", "best",
        "--label", label,
        "--out-dir", str(EVAL_OUT.relative_to(ROOT)),
    ]
    print(f"[swa] eval -> {label}: {' '.join(cmd)}", flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=ROOT)
    print(f"[swa] eval {label} rc={proc.returncode} dt={time.time()-t0:.1f}s",
          flush=True)
    return proc.returncode


def run_ranking(python_bin: str) -> int:
    cmd = [
        python_bin,
        str(ROOT / "evaluation" / "paper_grade_axes.py"),
        str(EVAL_OUT.relative_to(ROOT)),
    ]
    print(f"[swa] ranking: {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main(weights: tuple[float, ...], python_bin: str, *, force: bool) -> int:
    EVAL_OUT.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    for w in weights:
        ckpt_dir = make_swa_ckpts(w, force=force)
        label = _label_for(w)
        rc = run_eval(ckpt_dir, label, python_bin)
        summaries.append({
            "w_r21": float(w),
            "label": label,
            "ckpt_dir": str(ckpt_dir.relative_to(ROOT)),
            "eval_rc": int(rc),
        })

    rank_rc = run_ranking(python_bin)

    manifest_path = ROOT / "results" / "research_loop" / "r26_swa_manifest.json"
    manifest_path.write_text(json.dumps({
        "weights": list(weights),
        "summaries": summaries,
        "eval_dir": str(EVAL_OUT.relative_to(ROOT)),
        "ranking_rc": int(rank_rc),
        "generated_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }, indent=2))
    print(f"[swa] manifest -> {manifest_path}", flush=True)
    return 0 if rank_rc == 0 else rank_rc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--weights", type=float, nargs="*", default=list(WEIGHTS_DEFAULT),
                        help="R21 mixing weights (default: 0.50 0.80 0.90 0.95 0.98)")
    parser.add_argument("--python-bin", default=PYTHON_DEFAULT,
                        help="Python interpreter for subprocesses (default: WSL andes_venv)")
    parser.add_argument("--force", action="store_true",
                        help="Re-merge ckpts even if target dir is populated")
    args = parser.parse_args()
    sys.exit(main(tuple(args.weights), args.python_bin, force=args.force))
