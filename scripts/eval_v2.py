"""Thin repository-root adapter for the objective EVAL-v2 scorecard.

Usage:
    python scripts/eval_v2.py \
        --trace-dir results/r279_formal_evaluation/traces \
        --output-dir tmp/icems2026/eval_v2 \
        --overwrite

Exit code 0 means the post-hoc validity gate passed. Exit code 2 means the
diagnostic artifacts were written but one or more hard validity checks failed.
"""

# ruff: noqa: E402,I001

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.eval_v2 import main


if __name__ == "__main__":
    raise SystemExit(main())
