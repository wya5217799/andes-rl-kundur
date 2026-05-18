"""Numerical aggregation helpers for evaluation scores.

Single source of truth for the floored geometric mean used across the
paper-path scripts (``scripts/score_run.py``, the dual-eval helper
``evaluation/summary.py``, and the archived round drivers
``scripts/_archive/round_scripts/_r{69,70,75}_*.py``).

Logic-preserving extraction (R75): every call site previously wrote the
same ``math.exp(sum(math.log(max(v, 0.01))) / n)`` chain inline. This
module collapses them onto one helper so the floor constant and the
empty-input behavior are uniform.

The function is intentionally *not* duplicated under ``paper_grade_axes``
— that module is paper-cited (AD-14) and its inline copies stay as-is.
"""
from __future__ import annotations

import math
from collections.abc import Iterable

DEFAULT_FLOOR = 0.01


def floor_geo_mean(values: Iterable[float], floor: float = DEFAULT_FLOOR) -> float:
    """Geometric mean with a per-value floor (avoids ``log(0)``).

    Returns ``0.0`` for an empty input (matches the empty-aggregate
    convention used in ``score_run.aggregate_scores``).
    """
    vals = list(values)
    if not vals:
        return 0.0
    return math.exp(
        sum(math.log(max(v, floor)) for v in vals) / len(vals)
    )
