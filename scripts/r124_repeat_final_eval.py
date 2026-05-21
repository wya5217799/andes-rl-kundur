"""R124 post-hoc final-eval rerun (uses patched checkpoint_loader).

R124 training (75 ep, td3_afe_lstm s49) completed successfully but the
auto-`--final-eval` crashed because checkpoint_loader.py did not dispatch
``algo == 'td3_afe_lstm'``. R124 verdict requires a geo number, so this
script does the final dual-eval post-hoc with the patched loader.

Run (WSL only):
    /home/wya/andes_venv/bin/python scripts/r124_repeat_final_eval.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.evaluation.final_eval import run_final_eval  # noqa: E402


def main() -> None:
    save_dirs = [
        ROOT / "results" / "r124_w1_afe_s49",
        ROOT / "results" / "r127_w1_qr_afe_s54",
        ROOT / "results" / "r129_w1_qr51_s49",
    ]

    for sd in save_dirs:
        if not (sd / "agent_0_best.pt").exists():
            print(f"  [skip] {sd.name}: no agent_0_best.pt yet")
            continue

        # Clear stale error file so a fresh failure is visible
        err = sd / "final_eval_error.txt"
        if err.exists():
            err.unlink()

        print(f"\n=== {sd.name} ===")
        # Match R124 plan: paper-faithful V4Config + normalize-actions
        base = V4Config.paper_faithful()
        cfg = dataclasses.replace(base, action_penalty_mode="normalized")

        summary = run_final_eval(sd, env_config=cfg, eval_tracked=False)
        if summary is None:
            err = sd / "final_eval_error.txt"
            if err.exists():
                print(f"  FAILED — see {err}")
                print("  " + err.read_text(encoding="utf-8").splitlines()[0])
            else:
                print("  No ckpt to eval (skipped)")
        else:
            geo = summary.get("geo")
            cum_rf = summary.get("cum_rf")
            ls1 = summary.get("LS1")
            ls2 = summary.get("LS2")
            print(
                f"  geo={geo:.4f} cum_rf={cum_rf:.4f} "
                f"(LS1={ls1:.4f} LS2={ls2:.4f})"
                if geo is not None else f"  summary: {summary}"
            )


if __name__ == "__main__":
    main()
