"""Tests for ``memory/tools/query.py`` — CLI + library queries over the
claim ledger.

R50 optimization L — when the claim count crosses ~50 (we're at 58
post-R49), eyeballing CLM-*.md files becomes painful. ``query.py``
gives a small surface for the two queries that come up most often:

  query_by_tag(claims, "td3")               -> [CLM-...]  (status='current')
  query_best(claims, metric_name="6_axis", top=N) -> [CLM-...]
"""
from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from query import query_best, query_by_tag  # noqa: E402


def _claim(cid: str, **extra) -> dict:
    base = {
        "id": cid,
        "type": "finding",
        "trust": "V",
        "status": "current",
        "supersedes": [],
        "superseded_by": [],
        "provenance": ["x"],
    }
    base.update(extra)
    return base


def test_query_by_tag_filters_to_matching_claims():
    claims = {
        "CLM-A": _claim("CLM-A", tags=["td3", "h64"]),
        "CLM-B": _claim("CLM-B", tags=["sac", "h128"]),
        "CLM-C": _claim("CLM-C", tags=["td3", "production"]),
    }
    out = query_by_tag(claims, "td3")
    out_ids = {c["id"] for c in out}
    assert out_ids == {"CLM-A", "CLM-C"}


def test_query_by_tag_excludes_superseded_by_default():
    claims = {
        "CLM-A": _claim("CLM-A", tags=["td3"], status="current"),
        "CLM-B": _claim("CLM-B", tags=["td3"], status="superseded"),
    }
    out = query_by_tag(claims, "td3")
    out_ids = {c["id"] for c in out}
    assert out_ids == {"CLM-A"}, (
        f"superseded claims must be hidden by default; got {out_ids}"
    )


def test_query_by_tag_include_superseded_flag():
    claims = {
        "CLM-A": _claim("CLM-A", tags=["td3"], status="current"),
        "CLM-B": _claim("CLM-B", tags=["td3"], status="superseded"),
    }
    out = query_by_tag(claims, "td3", include_superseded=True)
    assert {c["id"] for c in out} == {"CLM-A", "CLM-B"}


def test_query_by_tag_empty_when_no_match():
    claims = {"CLM-A": _claim("CLM-A", tags=["sac"])}
    assert query_by_tag(claims, "missing-tag") == []


def test_query_best_returns_top_k_by_metric_value():
    claims = {
        "CLM-A": _claim("CLM-A", metric={"name": "6_axis", "value": 0.275}),
        "CLM-B": _claim("CLM-B", metric={"name": "6_axis", "value": 0.334}),
        "CLM-C": _claim("CLM-C", metric={"name": "6_axis", "value": 0.117}),
        "CLM-D": _claim("CLM-D", metric={"name": "6_axis", "value": 0.351}),
    }
    out = query_best(claims, metric_name="6_axis", top=2)
    out_ids = [c["id"] for c in out]
    assert out_ids == ["CLM-D", "CLM-B"]  # 0.351 then 0.334


def test_query_best_filters_to_named_metric():
    """Only claims whose metric.name equals the query name are returned."""
    claims = {
        "CLM-A": _claim("CLM-A", metric={"name": "6_axis", "value": 0.5}),
        "CLM-B": _claim("CLM-B", metric={"name": "settling_s", "value": 0.9}),
    }
    out = query_best(claims, metric_name="6_axis", top=10)
    assert [c["id"] for c in out] == ["CLM-A"]


def test_query_best_skips_claims_without_metric():
    claims = {
        "CLM-A": _claim("CLM-A", metric={"name": "6_axis", "value": 0.3}),
        "CLM-B": _claim("CLM-B"),  # no metric
    }
    out = query_best(claims, metric_name="6_axis", top=10)
    assert [c["id"] for c in out] == ["CLM-A"]


def test_query_best_top_zero_returns_empty():
    claims = {"CLM-A": _claim("CLM-A", metric={"name": "6_axis", "value": 0.3})}
    assert query_best(claims, metric_name="6_axis", top=0) == []
