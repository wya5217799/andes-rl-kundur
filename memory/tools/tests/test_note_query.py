"""Tests for note_query.py — filter / search over Note frontmatter."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from note_query import filter_notes, format_row  # noqa: E402

NOTE_FIXTURES = Path(__file__).parent / "fixtures" / "notes"


def test_filter_by_topic_top_level():
    hits = filter_notes(NOTE_FIXTURES, topic="training-infra")
    ids = [n["id"] for n in hits]
    assert "NOTE-0001" in ids
    assert "NOTE-0002" not in ids


def test_filter_by_sub_tag():
    hits = filter_notes(NOTE_FIXTURES, tag="src-layout")
    ids = [n["id"] for n in hits]
    assert "NOTE-0002" in ids


def test_filter_by_source():
    hits = filter_notes(NOTE_FIXTURES, source="adr-rationale")
    assert [n["id"] for n in hits] == ["NOTE-0002"]


def test_filter_by_round():
    hits = filter_notes(NOTE_FIXTURES, round_id="R58")
    ids = sorted(n["id"] for n in hits)
    assert ids == ["NOTE-0001", "NOTE-0003"]


def test_filter_by_grep_summary():
    """grep should match against summary text inside the body, not just frontmatter."""
    hits = filter_notes(NOTE_FIXTURES, grep="ADR-rationale fixture")
    assert [n["id"] for n in hits] == ["NOTE-0002"]


def test_format_row_one_line():
    notes = filter_notes(NOTE_FIXTURES, topic="training-infra")
    assert notes  # guard
    row = format_row(notes[0])
    assert notes[0]["id"] in row
    # 1-line row, length-capped
    assert "\n" not in row


def test_filter_no_args_returns_all():
    hits = filter_notes(NOTE_FIXTURES)
    assert len(hits) == 3
