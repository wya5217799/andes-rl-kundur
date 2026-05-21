"""R127 followup: post-hoc eval of both `best.pt` (train-reward-best) and
`final.pt` (end-of-training) for R124+R127+R129. Plus mid-training best.pt
for R122 (other session's td3_qr_lstm s54 — cross-seed verification of R129).

CLM-0255 (R124/R127/R129 closed-NEGATIVE) used best.pt only. If the
reward-gaming hypothesis is correct, best.pt is over-fit to a reward sweet
spot but final.pt is a fresher snapshot that might score differently.

Run (WSL only):
    /home/wya/andes_venv/bin/python scripts/r127_followup_final_vs_best_eval.py
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.evaluation.final_eval import (  # noqa: E402
    pick_final_eval_suffix,
    run_final_eval,
)
from andes_rl_kundur.evaluation.score_seed import score_seed  # noqa: E402


def main() -> None:
    targets = [
        ("r124_w1_afe_s49", "normalized"),       # AFE s49 (mine)
        ("r127_w1_qr_afe_s54", "normalized"),    # stacked s54 (mine)
        ("r129_w1_qr51_s49", "normalized"),      # QR s49 (mine)
        ("r122_w1_qr51_s54", "normalized"),      # QR s54 (other session, in-flight ok)
    ]

    base = V4Config.paper_faithful()
    cfg = dataclasses.replace(base, action_penalty_mode="normalized")

    for name, _ in targets:
        save_dir = ROOT / "results" / name
        if not save_dir.exists():
            print(f"\n[skip] {name}: dir missing")
            continue

        print(f"\n=== {name} ===")

        # Try both 'best' and 'final' suffixes if available
        for suffix in ("best", "final"):
            ckpt = save_dir / f"agent_0_{suffix}.pt"
            if not ckpt.exists():
                print(f"  [skip suffix={suffix}] no ckpt")
                continue

            label = f"{name}_{suffix}"
            out = save_dir / f"_post_hoc_eval_{suffix}"
            out.mkdir(parents=True, exist_ok=True)
            try:
                summary = score_seed(
                    save_dir,
                    label=label,
                    out_dir=out,
                    suffix=suffix,
                    seed=42,
                    steps=150,
                    config=cfg,
                )
            except Exception as exc:
                print(f"  [{suffix}] FAILED: {type(exc).__name__}: {str(exc)[:120]}")
                continue
            geo = summary.get("geo")
            ls1 = summary.get("LS1")
            ls2 = summary.get("LS2")
            cum = summary.get("cum_rf")
            print(
                f"  [{suffix}] geo={geo:.4f} LS1={ls1:.4f} LS2={ls2:.4f} cum_rf={cum:.4f}"
                if geo is not None
                else f"  [{suffix}] (None geo) summary={summary}"
            )


if __name__ == "__main__":
    main()
