"""Reserve next NOTE-NNNN id and scaffold a stub Note file.

Mirrors the pattern of reserve_round.py — atomic-ish: we read the highest
existing NOTE-NNNN, return max+1, and the caller writes a file at that id.
Concurrent races between sessions are mitigated by `scaffold_note` opening
the target file with ``x`` mode (fails if it already exists), prompting
the caller to retry with a higher id.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NOTE_ID_RE = re.compile(r"^NOTE-(\d+)\.md$")


def reserve_next_note_id(notes_dir: Path) -> int:
    """Return ``max(existing NOTE-NNNN ids) + 1``, or 1 if none exist.

    Skips ``_TEMPLATE.md`` and any non-NOTE-*.md files.
    """
    max_id = 0
    if notes_dir.exists():
        for entry in notes_dir.iterdir():
            if not entry.is_file():
                continue
            m = NOTE_ID_RE.match(entry.name)
            if not m:
                continue
            max_id = max(max_id, int(m.group(1)))
    return max_id + 1


def scaffold_note(
    notes_dir: Path,
    *,
    note_id: int,
    source: str,
    source_path: str,
    date: str,
    topics: list[str],
    related_rounds: list[str],
    summary: str = "",
) -> Path:
    """Write a NOTE-NNNN.md stub with the supplied frontmatter values.

    Raises FileExistsError if the target already exists (concurrent-write guard).
    """
    note_filename = f"NOTE-{note_id:04d}.md"
    target = notes_dir / note_filename
    related_rounds_yaml = "[" + ", ".join(related_rounds) + "]"
    topics_yaml = "[" + ", ".join(topics) + "]"
    body = f"""---
id: NOTE-{note_id:04d}
source: {source}
source_path: {source_path}
date: {date}
related_rounds: {related_rounds_yaml}
topics: {topics_yaml}
extracted_claims: []
status: ingested
---

## Summary
{summary or "<3-5 sentences>"}

## Key facts (claim candidates)
- <bullet>

## Related pointers
- <Pointers only; not task state. Put active work in Q-NNNN or the selected LINE.md.>
"""
    with target.open("x", encoding="utf-8") as f:
        f.write(body)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold the next NOTE-NNNN.md")
    base = Path(__file__).parent.parent
    parser.add_argument("--notes-dir", type=Path, default=base / "notes")
    # Import inside main() so --help stays fast (avoids pulling yaml at startup).
    # Schema authority for the source enum is validate.py; importing avoids
    # CLI drift if the enum grows a new source type.
    from validate import NOTE_SOURCE_ENUM  # noqa: E402

    parser.add_argument("--source", required=True,
                        choices=sorted(NOTE_SOURCE_ENUM))
    parser.add_argument("--source-path", required=True,
                        help="repo-relative path to the original file")
    parser.add_argument("--date", required=True, help="YYYY-MM-DD of original source")
    parser.add_argument("--topic", action="append", required=True,
                        help="topic (first one is top-level); repeat for sub-tags")
    parser.add_argument("--round", action="append", default=[], dest="rounds",
                        help="related round (e.g. R58); repeat as needed")
    parser.add_argument("--summary", default="", help="optional one-line summary")
    args = parser.parse_args()

    note_id = reserve_next_note_id(args.notes_dir)
    path = scaffold_note(
        args.notes_dir,
        note_id=note_id,
        source=args.source,
        source_path=args.source_path,
        date=args.date,
        topics=args.topic,
        related_rounds=args.rounds,
        summary=args.summary,
    )
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
