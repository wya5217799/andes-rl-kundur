#!/usr/bin/env python3
"""R293 fresh-bank generator and corrected q0 completion/physics screen."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "scripts/run_r292_fresh_bank.py"
SPEC = importlib.util.spec_from_file_location("run_r293_fresh_bank_core", CORE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load fresh-bank core: {CORE_PATH}")
CORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CORE)

from andes_rl_kundur.evaluation.r292_screen import (  # noqa: E402
    audit_r292_q0_screen_record,
)
from andes_rl_kundur.evaluation.r292_screen_bank import (  # noqa: E402
    assess_r292_screened_bank,
)

CORE.ROUND_ID = "R293"
CORE.QUESTION_ID = "Q-0050"
CORE.CANDIDATE_SEED = 2026080203
CORE.TRAINING_SUMMARY = (
    ROOT / "results/r293_prior_residual_training/training_matrix_summary.json"
)
CORE.DEFAULT_SEAL = ROOT / "memory/rounds/R293/fresh_bank_screen_seal.json"
CORE.DEFAULT_OUT = ROOT / "results/r293_fresh_bank"
CORE.FORMAL_TRACE_DIR = ROOT / "results/r293_formal_evaluation/traces"
CORE.audit_zero_support_screen_record = audit_r292_q0_screen_record
CORE.assess_screened_authority_bank = assess_r292_screened_bank


def _verify_training(training: dict[str, Any]) -> None:
    if not training.get("all_completed") or training.get("observed_run_count") != 10:
        raise ValueError("fresh bank requires ten completed R293 training runs")
    if training.get("seed_selection_performed") is not False:
        raise ValueError("training summary reports forbidden seed selection")
    for path_text, digest in training.get("artifact_hashes", {}).items():
        if CORE.sha256_file(ROOT / path_text) != digest:
            raise ValueError(f"training artifact drift: {path_text}")


def _source_paths() -> dict[str, Path]:
    return {
        "plan": ROOT / "memory/rounds/R293/plan.md",
        "adapter": Path(__file__).resolve(),
        "fresh_bank_core": CORE_PATH,
        "vector_runner": ROOT
        / "src/andes_rl_kundur/evaluation/vector_residual.py",
        "r293_q0_record_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen.py",
        "r293_q0_bank_audit": ROOT
        / "src/andes_rl_kundur/evaluation/r292_screen_bank.py",
        "prospective_authority": ROOT
        / "src/andes_rl_kundur/evaluation/prospective_authority.py",
        "sealed_bank": ROOT / "src/andes_rl_kundur/evaluation/sealed_bank.py",
        "training_summary": CORE.TRAINING_SUMMARY,
        "reference_bank": CORE.REFERENCE_BANK,
    }


CORE._verify_training = _verify_training
CORE._source_paths = _source_paths


if __name__ == "__main__":
    CORE.main()
