"""Tests for the floored geometric-mean helper extracted in R75.

The function replaces 4 inline copies of the same formula previously in
``scripts/score_run.py`` and three R-driver scripts now archived under
``scripts/_archive/round_scripts/_r{69,70,75}_*.py``. These tests pin
the contract so future changes to the helper cannot silently shift the
headline 6-axis number.
"""
from __future__ import annotations

import math

import pytest

from andes_rl_kundur.evaluation.aggregation import (
    DEFAULT_FLOOR,
    floor_geo_mean,
)


def _legacy_formula(values, floor=0.01):
    """The exact inline expression used in all 4 prior call sites."""
    return math.exp(sum(math.log(max(v, floor)) for v in values) / len(values))


def test_default_floor_matches_inline_formula():
    vals = [0.30, 0.42, 0.18, 0.55]
    assert floor_geo_mean(vals) == pytest.approx(_legacy_formula(vals))


def test_floors_zero_to_default():
    """A 0 in the input should not raise (would be log(0) without floor)."""
    vals = [0.5, 0.0, 0.4]
    expected = _legacy_formula(vals)  # uses max(0, 0.01) = 0.01
    assert floor_geo_mean(vals) == pytest.approx(expected)


def test_negative_floors_to_default():
    """Negative values clamp to the floor (matches prior behavior)."""
    vals = [0.3, -0.1, 0.4]
    expected = _legacy_formula(vals)
    assert floor_geo_mean(vals) == pytest.approx(expected)


def test_custom_floor():
    vals = [0.0, 0.5]
    assert floor_geo_mean(vals, floor=0.05) == pytest.approx(
        math.exp((math.log(0.05) + math.log(0.5)) / 2)
    )


def test_empty_returns_zero():
    """Empty input is the only intentional behavior change vs. the legacy
    inline formula (which would raise ZeroDivisionError). Matches the
    empty-aggregate convention in ``score_run.aggregate_scores``."""
    assert floor_geo_mean([]) == 0.0


def test_iterable_input_consumed_once():
    """Should work with a generator (the call sites pass dict.values())."""
    vals = (v for v in [0.2, 0.3, 0.4])
    expected = _legacy_formula([0.2, 0.3, 0.4])
    assert floor_geo_mean(vals) == pytest.approx(expected)


def test_default_floor_constant():
    assert DEFAULT_FLOOR == 0.01
