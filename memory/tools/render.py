"""Render memory/STATE.md as an active oracle.

Six sections, in order:
1. Headline Numbers — claims tagged `headline`, status=current
2. In-Flight — round dirs with plan.md but no verdict*.md
3. Open Questions — Q files with status in {open, in-flight}
4. Recently Closed — last 3 Q files with status starting with `closed-`
5. Latest Round — newest RNN dir + one-line TL;DR from its verdict
6. Stats — counts

Handoffs are intentionally not rendered (see memory/handoffs/README.md).
"""
from __future__ import annotations
import argparse
import datetime as dt
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TLDR_BLOCK_RE = re.compile(
    r"^##\s+TL;DR\s*\n+(.*?)(?=\n##\s|\Z)", re.MULTILINE | re.DOTALL
)
ROUND_DIR_RE = re.compile(r"^R(\d+)$")


# ---------- loaders ----------


def _load_yaml_frontmatter(path: Path) -> dict[str, Any] | None:
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return None
    return yaml.safe_load(match.group(1)) or {}


def _load_claims(claims_dir: Path) -> list[dict[str, Any]]:
    claims = []
    for path in sorted(claims_dir.glob("CLM-*.md")):
        meta = _load_yaml_frontmatter(path)
        if meta is not None:
            claims.append(meta)
    return claims


def _load_questions(questions_dir: Path) -> list[dict[str, Any]]:
    if not questions_dir.exists():
        return []
    qs = []
    for path in sorted(questions_dir.glob("Q-*.md")):
        meta = _load_yaml_frontmatter(path)
        if meta is not None:
            qs.append(meta)
    return qs


def _iter_round_dirs(rounds_dir: Path) -> list[Path]:
    dirs = []
    if not rounds_dir.exists():
        return dirs
    for p in rounds_dir.iterdir():
        if p.is_dir() and ROUND_DIR_RE.match(p.name):
            dirs.append(p)
    dirs.sort(key=lambda d: int(ROUND_DIR_RE.match(d.name).group(1)))
    return dirs


def _round_verdict_path(round_dir: Path) -> Path | None:
    """Return the canonical verdict.md if present, else the first
    *verdict*.md found alphabetically, else None."""
    canonical = round_dir / "verdict.md"
    if canonical.exists():
        return canonical
    for alt in sorted(round_dir.glob("*verdict*.md")):
        return alt
    return None


def _round_is_in_flight(round_dir: Path) -> bool:
    """A round is in-flight if it has a plan.md but no verdict*.md."""
    plan = round_dir / "plan.md"
    return plan.exists() and _round_verdict_path(round_dir) is None


def _extract_tldr(verdict_path: Path | None) -> str | None:
    """Return the first non-trivial line of a verdict's `## TL;DR` block, or None.

    Skips:
    - empty lines
    - HTML comments (`<!-- ... -->`)
    - Markdown horizontal rules (`---`, `***`, `___`)

    If the body is entirely a blockquote (lines starting with `>`), returns
    the first quoted line with the `>` prefix stripped. This way verdicts
    that put their summary in a single blockquote still surface a usable
    one-line summary in STATE.md.
    """
    if verdict_path is None or not verdict_path.exists():
        return None
    text = verdict_path.read_text(encoding="utf-8")
    match = TLDR_BLOCK_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()

    def _is_skip(line: str) -> bool:
        if not line:
            return True
        if line.startswith("<!--"):
            return True
        # Markdown horizontal rules: a line that is only -, *, or _ chars
        if set(line) <= {"-"} and len(line) >= 3:
            return True
        if set(line) <= {"*"} and len(line) >= 3:
            return True
        if set(line) <= {"_"} and len(line) >= 3:
            return True
        return False

    # First pass: take any non-trivial non-blockquote line.
    for raw in body.splitlines():
        line = raw.strip()
        if _is_skip(line) or line.startswith(">"):
            continue
        return line

    # Fallback: body is entirely blockquoted. Return first quoted line
    # with the leading `>` (and optional space) stripped.
    for raw in body.splitlines():
        line = raw.strip()
        if not line.startswith(">"):
            continue
        stripped = line.lstrip("> ").strip()
        if stripped and not _is_skip(stripped):
            return stripped
    return None


# ---------- section formatters ----------


def _format_headline_line(claim: dict[str, Any]) -> str:
    cid = claim["id"]
    trust = claim.get("trust", "?")
    statement = (claim.get("statement") or "").strip().splitlines()[0]
    round_label = claim.get("round")
    suffix = f" ({round_label})" if round_label else ""
    return f"- {cid} [{trust}] {statement}{suffix}"


def _format_open_q_line(q: dict[str, Any]) -> str:
    qid = q["id"]
    title = q.get("title", "(no title)")
    opened = q.get("opened_round", "?")
    return f"- {qid} [opened {opened}] {title}"


def _format_closed_q_line(q: dict[str, Any]) -> str:
    qid = q["id"]
    title = q.get("title", "(no title)")
    status = q.get("status", "?")
    closed_round = q.get("closed_round", "?")
    closed_by = q.get("closed_by", "?")
    return f"- {qid} {status} @ {closed_round}, by {closed_by} — {title}"


# ---------- top-level render ----------


def render_state(
    claims_dir: Path,
    rounds_dir: Path,
    questions_dir: Path,
    out_path: Path,
) -> None:
    claims = _load_claims(claims_dir)
    questions = _load_questions(questions_dir)
    round_dirs = _iter_round_dirs(rounds_dir)

    headlines = [
        c for c in claims
        if c.get("status") == "current" and "headline" in (c.get("tags") or [])
    ]

    in_flight_rounds = [d for d in round_dirs if _round_is_in_flight(d)]
    completed_rounds = [d for d in round_dirs if not _round_is_in_flight(d)]

    open_qs = [
        q for q in questions
        if q.get("status") in ("open", "in-flight")
    ]

    def _closed_round_num(q: dict[str, Any]) -> int:
        """Numeric key for sorting closed Qs by closing round.
        Lexicographic sort would put `R10` before `R9`; this parses the
        digit suffix so the sort is correct regardless of zero-padding."""
        cr = q.get("closed_round") or ""
        m = ROUND_DIR_RE.match(cr)
        return int(m.group(1)) if m else -1

    closed_qs = sorted(
        (q for q in questions if (q.get("status") or "").startswith("closed-")),
        key=_closed_round_num,
        reverse=True,
    )[:3]

    # "Latest Round" is the newest *completed* round, so it doesn't double
    # up with the In-Flight section when the highest-numbered round is
    # plan-only. Fallback: if no round has a verdict, point at the newest
    # in-flight round (so STATE.md isn't empty during the very first round).
    latest_round = (
        completed_rounds[-1] if completed_rounds
        else (round_dirs[-1] if round_dirs else None)
    )
    latest_tldr = (
        _extract_tldr(_round_verdict_path(latest_round)) if latest_round else None
    )

    type_counts = Counter(c.get("type", "?") for c in claims)
    open_count = sum(
        1 for q in questions if q.get("status") in ("open", "in-flight")
    )
    closed_count = sum(
        1 for q in questions if (q.get("status") or "").startswith("closed-")
    )

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append(f"# Project State — auto-rendered {now}")
    lines.append("")
    lines.append("> Do not edit this file. Regenerate via `python memory/tools/render.py`.")
    lines.append("")

    # 1. Headlines
    lines.append("## Headline Numbers")
    lines.append("")
    if headlines:
        lines.extend(_format_headline_line(c) for c in headlines)
    else:
        lines.append("(none)")
    lines.append("")

    # 2. In-Flight
    lines.append("## In-Flight")
    lines.append("")
    if in_flight_rounds:
        for d in in_flight_rounds:
            lines.append(f"- {d.name} — `memory/rounds/{d.name}/plan.md`")
    else:
        lines.append("(none)")
    lines.append("")

    # 3. Open Questions
    lines.append("## Open Questions")
    lines.append("")
    if open_qs:
        lines.extend(_format_open_q_line(q) for q in open_qs)
    else:
        lines.append("(none)")
    lines.append("")

    # 4. Recently Closed
    lines.append("## Recently Closed (last 3)")
    lines.append("")
    if closed_qs:
        lines.extend(_format_closed_q_line(q) for q in closed_qs)
    else:
        lines.append("(none)")
    lines.append("")

    # 5. Latest Round
    lines.append("## Latest Round")
    lines.append("")
    if latest_round:
        verdict = _round_verdict_path(latest_round)
        tldr_text = latest_tldr or "(no TL;DR yet)"
        ref = (
            f"see `memory/rounds/{latest_round.name}/{verdict.name}`"
            if verdict
            else f"see `memory/rounds/{latest_round.name}/plan.md` (in-flight)"
        )
        lines.append(f"{latest_round.name} — {tldr_text}")
        lines.append("")
        lines.append(ref)
    else:
        lines.append("(no rounds yet)")
    lines.append("")

    # 6. Stats
    lines.append("## Stats")
    lines.append("")
    stats = (
        f"{len(claims)} claims "
        f"({type_counts.get('finding', 0)} finding / "
        f"{type_counts.get('decision', 0)} decision / "
        f"{type_counts.get('correction', 0)} correction) · "
        f"{len(round_dirs)} rounds · "
        f"{len(questions)} questions "
        f"({open_count} open / {closed_count} closed)"
    )
    lines.append(stats)
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render memory/STATE.md")
    base = Path(__file__).parent.parent
    parser.add_argument("--claims-dir", type=Path, default=base / "claims")
    parser.add_argument("--rounds-dir", type=Path, default=base / "rounds")
    parser.add_argument("--questions-dir", type=Path, default=base / "questions")
    parser.add_argument("--out", type=Path, default=base / "STATE.md")
    args = parser.parse_args()
    render_state(args.claims_dir, args.rounds_dir, args.questions_dir, args.out)
    print(f"Rendered {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
