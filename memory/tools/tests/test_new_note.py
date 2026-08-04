"""Tests for memory/tools/new_note.py — atomic Note id reservation."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from new_note import reserve_next_note_id, scaffold_note  # noqa: E402


def test_reserve_next_note_id_empty_dir(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    assert reserve_next_note_id(notes_dir) == 1


def test_reserve_next_note_id_skips_template(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "_TEMPLATE.md").write_text("template")
    assert reserve_next_note_id(notes_dir) == 1


def test_reserve_next_note_id_existing(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "NOTE-0001.md").write_text("placeholder")
    (notes_dir / "NOTE-0003.md").write_text("placeholder")  # gap is fine
    assert reserve_next_note_id(notes_dir) == 4


def test_scaffold_note_writes_valid_frontmatter(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    path = scaffold_note(
        notes_dir,
        note_id=7,
        source="handoff",
        source_path="memory/handoffs/example.md",
        date="2026-05-17",
        topics=["training-infra", "lstm"],
        related_rounds=["R58"],
        summary="One line summary.",
    )
    assert path.name == "NOTE-0007.md"
    text = path.read_text(encoding="utf-8")
    assert "id: NOTE-0007" in text
    assert "source: handoff" in text
    assert "training-infra" in text
    assert "One line summary." in text
    assert "## Related pointers" in text
    assert "not task state" in text
    assert "## Open threads" not in text
