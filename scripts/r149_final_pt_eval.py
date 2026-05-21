"""Re-eval R149 with final.pt (instead of best.pt) to test if train-eval
mismatch hypothesis: best.pt picked at ep 102 over-fit train_reward;
final.pt at ep 200 might or might not be different.

Then also include R149 in HAWE 4-way ensemble if it's good.
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.env.andes.v4_config import V4Config  # noqa: E402
from andes_rl_kundur.evaluation.score_seed import score_seed  # noqa: E402


def main() -> None:
    base = V4Config.paper_faithful()
    cfg = dataclasses.replace(base, action_penalty_mode="normalized")

    for suffix in ("best", "final"):
        sd = ROOT / "results" / "r149_qr51_s54_200ep"
        if not (sd / f"agent_0_{suffix}.pt").exists():
            print(f"[skip] {suffix}: no ckpt")
            continue
        out = sd / f"_post_hoc_eval_{suffix}"
        out.mkdir(parents=True, exist_ok=True)
        try:
            summary = score_seed(
                sd,
                label=f"r149_post_{suffix}",
                out_dir=out,
                suffix=suffix,
                seed=42,
                steps=150,
                config=cfg,
            )
        except Exception as exc:
            print(f"[{suffix}] FAILED: {type(exc).__name__}: {str(exc)[:120]}")
            continue
        geo = summary.get("geo")
        ls1 = summary.get("LS1")
        ls2 = summary.get("LS2")
        cum = summary.get("cum_rf")
        print(
            f"[{suffix}] geo={geo:.4f} LS1={ls1:.4f} LS2={ls2:.4f} cum_rf={cum:.4f}"
            if geo is not None else f"[{suffix}] summary={summary}"
        )


if __name__ == "__main__":
    main()
