"""Integrity-only R277 analysis compatibility repair.

The sealed trace summariser inherited from R275 does not expose the storage
saturation-reason count expected by the R277 outcome selector.  This module
adds that already-recorded field without changing a trace, endpoint, guard,
threshold, or selection rule.
"""

from typing import Any

from andes_rl_kundur.evaluation.learning_gap_oracle import (
    summarise_learning_gap_trace as _sealed_summarise_learning_gap_trace,
)


def summarise_learning_gap_trace_with_saturation_count(
    record: dict[str, Any],
    *,
    final_window_steps: int = 50,
    fast_window_steps: int = 15,
) -> dict[str, Any]:
    """Return the sealed summary plus its missing saturation-reason count."""
    summary = _sealed_summarise_learning_gap_trace(
        record,
        final_window_steps=final_window_steps,
        fast_window_steps=fast_window_steps,
    )
    summary["bess_saturation_reason_count"] = sum(
        bool(reason)
        for step in record["traces"]
        for reason in step.get("bess_saturation_reasons", [])
    )
    return summary
