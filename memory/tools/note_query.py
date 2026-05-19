"""Filter and search notes by topic / source / round / free-text grep.

CLI:
    python memory/tools/note_query.py --topic training-infra
    python memory/tools/note_query.py --tag lstm --round R58
    python memory/tools/note_query.py --grep "hyperparameter sweep"
    python memory/tools/note_query.py --source-path memory/handoffs/foo.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
ROW_MAX_LEN = 200


def _load_note(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    meta = yaml.safe_load(match.group(1)) or {}
    meta["_path"] = path
    meta["_body"] = text[match.end():]
    return meta


def filter_notes(
    notes_dir: Path,
    *,
    topic: str | None = None,
    tag: str | None = None,
    source: str | None = None,
    round_id: str | None = None,
    source_path: str | None = None,
    grep: str | None = None,
) -> list[dict[str, Any]]:
    """Return notes matching all supplied filters.

    Filters are AND-combined. ``topic`` matches only against ``topics[0]``
    (top-level); ``tag`` matches any element of ``topics`` (top or sub).
    ``grep`` is a substring search across both frontmatter (yaml dump) and
    body text. ``round_id`` matches any element of ``related_rounds``.
    """
    if not notes_dir.exists():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(notes_dir.glob("NOTE-*.md")):
        note = _load_note(path)
        if note is None:
            continue
        if topic is not None:
            topics = note.get("topics") or []
            if not topics or topics[0] != topic:
                continue
        if tag is not None:
            if tag not in (note.get("topics") or []):
                continue
        if source is not None and note.get("source") != source:
            continue
        if round_id is not None:
            if round_id not in (note.get("related_rounds") or []):
                continue
        if source_path is not None and note.get("source_path") != source_path:
            continue
        if grep is not None:
            haystack = (
                yaml.safe_dump(
                    {k: v for k, v in note.items() if not k.startswith("_")},
                    allow_unicode=True,
                )
                + (note.get("_body") or "")
            )
            if grep.lower() not in haystack.lower():
                continue
        out.append(note)
    return out


def format_row(note: dict[str, Any]) -> str:
    """One-line summary suitable for CLI output."""
    nid = note.get("id", "?")
    source = note.get("source", "?")
    topics = note.get("topics") or []
    topic = topics[0] if topics else "?"
    # Pull first non-blank line of body Summary section
    body = note.get("_body") or ""
    summary = ""
    in_summary = False
    for line in body.splitlines():
        if line.strip().startswith("## Summary"):
            in_summary = True
            continue
        if in_summary:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("##"):
                break
            summary = stripped
            break
    row = f"{nid} [{topic}/{source}] {summary}"
    if len(row) > ROW_MAX_LEN:
        row = row[: ROW_MAX_LEN - 1] + "…"
    return row


def main() -> int:
    parser = argparse.ArgumentParser(description="Filter / search memory/notes/")
    base = Path(__file__).parent.parent
    parser.add_argument("--notes-dir", type=Path, default=base / "notes")
    parser.add_argument("--topic", help="filter by top-level topic")
    parser.add_argument("--tag", help="filter by any (top or sub) tag")
    # Import inside main() so `note_query --help` doesn't pay the yaml-import
    # cost from validate.py. Schema authority for the source enum is validate.py;
    # importing avoids drift if validate.py grows a new source type.
    from validate import NOTE_SOURCE_ENUM  # noqa: E402

    parser.add_argument(
        "--source",
        choices=sorted(NOTE_SOURCE_ENUM),
    )
    parser.add_argument("--round", dest="round_id", help="filter by related round (e.g. R58)")
    parser.add_argument("--source-path", help="exact source_path match (reverse lookup)")
    parser.add_argument("--grep", help="substring search in body + frontmatter")
    args = parser.parse_args()

    hits = filter_notes(
        args.notes_dir,
        topic=args.topic,
        tag=args.tag,
        source=args.source,
        round_id=args.round_id,
        source_path=args.source_path,
        grep=args.grep,
    )
    for note in hits:
        print(format_row(note))
    print(f"# {len(hits)} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
