"""TraceScore.summary() ASCII-bar formatting contract.

Pinned in R77 follow-up to R76 review NIT-2: the legacy
``int(score * 20) + int((1 - score) * 20)`` formula produces a bar of
width 19 instead of 20 whenever the two ``int()`` truncations both
round down (e.g. score = 0.333 → 6 + 13 = 19). The bar should be
exactly ``_SCORE_BAR_WIDTH`` columns wide for every score in ``[0, 1]``
so downstream log parsing / column alignment is stable.

This is a print-only behavior — no 6-axis numerical change. Pinned so
a future refactor cannot silently regress the visual width.
"""
from __future__ import annotations

import pytest

from andes_rl_kundur.evaluation.paper_grade_axes import (
    _SCORE_BAR_WIDTH,
    AxisScore,
    TraceScore,
)


def _extract_bar(summary_text: str, axis_name: str) -> str:
    """Pull the ``[####....]`` segment for a named axis out of the
    multi-line summary block."""
    for line in summary_text.splitlines():
        if axis_name in line and "[" in line and "]" in line:
            return line[line.index("[") + 1 : line.index("]")]
    raise AssertionError(f"axis {axis_name} not found in summary:\n{summary_text}")


@pytest.mark.parametrize(
    "score",
    [0.0, 0.1, 0.25, 0.333, 0.5, 0.6, 0.7, 0.875, 0.999, 1.0],
)
def test_summary_bar_width_constant(score: float):
    ts = TraceScore(
        label="test_label",
        scenario="load_step_1",
        is_ddic=True,
        axes=[AxisScore(name="probe_axis", project_value=0.0,
                        paper_value=0.0, score=score, note="")],
        overall=score,
    )
    bar = _extract_bar(ts.summary(), "probe_axis")
    assert len(bar) == _SCORE_BAR_WIDTH, (
        f"score={score}: bar width {len(bar)} != "
        f"_SCORE_BAR_WIDTH={_SCORE_BAR_WIDTH}; bar={bar!r}"
    )


def test_summary_bar_endpoints():
    """score=0 → all dots; score=1 → all hashes."""
    ts0 = TraceScore(
        label="lo", scenario="s", is_ddic=True,
        axes=[AxisScore(name="ax", project_value=0, paper_value=0, score=0.0)],
        overall=0.0,
    )
    ts1 = TraceScore(
        label="hi", scenario="s", is_ddic=True,
        axes=[AxisScore(name="ax", project_value=0, paper_value=0, score=1.0)],
        overall=1.0,
    )
    bar0 = _extract_bar(ts0.summary(), "ax")
    bar1 = _extract_bar(ts1.summary(), "ax")
    assert bar0 == "." * _SCORE_BAR_WIDTH
    assert bar1 == "#" * _SCORE_BAR_WIDTH


def test_summary_bar_proportional():
    """For score=0.5 the bar is half hashes, half dots."""
    ts = TraceScore(
        label="m", scenario="s", is_ddic=True,
        axes=[AxisScore(name="ax", project_value=0, paper_value=0, score=0.5)],
        overall=0.5,
    )
    bar = _extract_bar(ts.summary(), "ax")
    half = _SCORE_BAR_WIDTH // 2
    assert bar == "#" * half + "." * (_SCORE_BAR_WIDTH - half)
