"""Prospective source-bound EVAL view for fresh model-first Stage-1 records."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def build_fresh_stage1_eval_view(
    record: dict[str, Any],
    *,
    source_path: str,
    source_sha256: str,
    expected_round: str = "R310",
    expected_question: str = "Q-0066",
) -> dict[str, Any]:
    """Return the paired EVAL metadata view without mutating the source record."""

    if (
        record.get("round") != expected_round
        or record.get("question") != expected_question
    ):
        raise ValueError("EVAL view record does not match declared round/question")
    if not str(record.get("coordinate", "")).startswith("edge_"):
        raise ValueError("EVAL view accepts only Stage-1 edge records")
    pulse_sign = record.get("sign")
    if pulse_sign not in {"positive", "negative"}:
        raise ValueError("edge record sign must be positive or negative")
    if record.get("controller") != pulse_sign:
        raise ValueError("controller must retain the pulse-sign identity")
    if not source_path:
        raise ValueError("source_path must be non-empty")
    if len(source_sha256) != 64:
        raise ValueError("source_sha256 must be a 64-character digest")

    view = deepcopy(record)
    view["sign"] = "paired"
    view["pulse_sign"] = pulse_sign
    view["source_record"] = {
        "path": source_path,
        "sha256": source_sha256,
    }
    return view
