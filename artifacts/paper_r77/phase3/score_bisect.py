"""Score every e3_bisect_R{NN}_<SHA>/ ckpt under the current main-worktree
v3.1 ranker and write `final_eval_summary.json` per directory.

bisect.sh only trains — eval is intentionally deferred so that every
commit is scored under the SAME ranker (the current main-worktree v3.1
paper_grade_axes.py). That way the cliff between adjacent commits
reflects training-time code drift, not ranker drift.

Run from repo root with the WSL ANDES interpreter:

    /home/wya/andes_venv/bin/python artifacts/paper_r77/phase3/score_bisect.py

Skips directories that already have `final_eval_summary.json` (idempotent
— safe to re-run after bisect.sh produces a new R{NN} dir).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ROOT = REPO / "results" / "r77_phase3"

sys.path.insert(0, str(REPO / "src"))

from andes_rl_kundur.evaluation.score_seed import score_seed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only", nargs="+", default=None,
        help="Optional SHA substrings (e.g. e8427df 43d203b) to restrict scoring. "
             "Use this while bisect.sh is still running to avoid scoring a dir "
             "whose ckpts are mid-write.",
    )
    args = parser.parse_args()

    dirs = sorted(d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("e3_bisect_"))
    if args.only:
        dirs = [d for d in dirs if any(sha in d.name for sha in args.only)]
    if not dirs:
        print(f"[score_bisect] no e3_bisect_* dirs under {ROOT}")
        return 1

    print(f"[score_bisect] {len(dirs)} bisect dirs found")
    for d in dirs:
        summary_path = d / "final_eval_summary.json"
        if summary_path.exists():
            r = json.loads(summary_path.read_text())
            print(f"  {d.name:55s}  SKIP (have summary geo={r.get('geo'):.4f})")
            continue

        best_pt = d / "agent_0_best.pt"
        if not best_pt.exists():
            print(f"  {d.name:55s}  SKIP (no agent_0_best.pt — training crashed?)")
            continue

        t0 = time.time()
        print(f"  {d.name:55s}  scoring ...", flush=True)
        rec = score_seed(
            d, label=d.name, out_dir=d, suffix="best", seed=42, steps=150,
        )
        summary_path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        dt = time.time() - t0
        print(
            f"    -> geo={rec['geo']:.4f}  cum_rf={rec['cum_rf']:.4f}  "
            f"LS1={rec['LS1']:.4f}  LS2={rec['LS2']:.4f}  ({dt:.0f}s)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
