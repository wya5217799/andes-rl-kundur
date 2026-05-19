"""Render memory/STATE.md as an active oracle.

Sections, in order:
0. (R≥59) 给 PI 的简报（最新一轮） — extracted from newest R≥59 verdict's
   `## 给 PI 的话` body, with `memory/glossary.yml` first-use annotation
1. Headline Numbers — claims tagged `headline`, status=current
2. In-Flight — round dirs with plan.md but no verdict*.md
3. Open Questions — Q files with status in {open, in-flight}
4. Recently Closed — last 3 Q files with status starting with `closed-`
5. Latest Round — newest RNN dir + one-line TL;DR from its verdict
5b. Leaderboard (optional) — claims with structured metric block
6. Stats — counts
7. (R≥59) 历史简报 — one-line headline per past R≥59 round (newest 5)

Handoffs are intentionally not rendered (see memory/handoffs/README.md).
PI briefing layer designed in ADR-0003.
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

# PI briefing extraction (ADR-0003). Mirrors validate.py constants.
PI_BRIEFING_CUTOFF = 59
PI_BRIEFING_SECTION = "## 给 PI 的话"
PI_BRIEFING_BLOCK_RE = re.compile(
    rf"^{re.escape(PI_BRIEFING_SECTION)}\s*\n+(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)
# The "结果（一句话）" sub-segment line — used for the 历史简报 section.
# Matches a bolded "结果（一句话）" label followed by its content on the
# same line.
PI_BRIEFING_HEADLINE_RE = re.compile(
    r"\*\*结果（一句话）\*\*[：:]\s*(.+?)(?:\n|$)"
)
# Historical briefings section: how many past R≥59 rounds to surface.
HISTORICAL_BRIEFINGS_KEEP = 5


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


def _round_state(round_dir: Path) -> str | None:
    """Return the lifecycle state declared in plan.md frontmatter.

    Returns None if plan.md or frontmatter is missing. Callers that need
    a state for legacy plans should treat None as equivalent to "active".
    """
    plan = round_dir / "plan.md"
    if not plan.exists():
        return None
    fm = _load_yaml_frontmatter(plan)
    if not fm:
        return None
    state = fm.get("state")
    return state if isinstance(state, str) else None


def _round_opened(round_dir: Path) -> str | None:
    """Return the `opened` date string from plan.md frontmatter, or None."""
    plan = round_dir / "plan.md"
    if not plan.exists():
        return None
    fm = _load_yaml_frontmatter(plan)
    if not fm:
        return None
    opened = fm.get("opened")
    if opened is None:
        return None
    return str(opened)


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


# ---------- PI briefing layer (ADR-0003) ----------


def _round_num(round_dir: Path) -> int:
    """Numeric round id from a directory name like R59. Used for cutoff
    filtering and chronological sort."""
    m = ROUND_DIR_RE.match(round_dir.name)
    return int(m.group(1)) if m else -1


def _extract_pi_briefing(verdict_path: Path | None) -> str | None:
    """Return the body of `## 给 PI 的话` from a verdict, or None.

    Body is stripped of surrounding whitespace; sub-segment formatting
    (the five **bold** labels) is preserved verbatim.
    """
    if verdict_path is None or not verdict_path.exists():
        return None
    text = verdict_path.read_text(encoding="utf-8")
    match = PI_BRIEFING_BLOCK_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    return body or None


def _extract_pi_briefing_headline(verdict_path: Path | None) -> str | None:
    """Extract just the `**结果（一句话）**` line from a briefing.

    Used for the `## 历史简报` section so older rounds appear as one-liners
    rather than full briefings.
    """
    body = _extract_pi_briefing(verdict_path)
    if not body:
        return None
    m = PI_BRIEFING_HEADLINE_RE.search(body)
    return m.group(1).strip() if m else None


def _load_glossary(glossary_path: Path) -> dict[str, str]:
    """Load memory/glossary.yml. Returns empty dict on missing file or
    parse error — annotation gracefully no-ops in that case."""
    if not glossary_path.exists():
        return {}
    try:
        data = yaml.safe_load(glossary_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        str(k): str(v).strip()
        for k, v in data.items()
        if isinstance(v, (str, int, float)) and str(v).strip()
    }


def _annotate_first_use(text: str, glossary: dict[str, str]) -> str:
    """Annotate first occurrence of each glossary term as `term(definition)`.

    Subsequent occurrences in the same text are left bare. Matching uses
    ASCII-word lookarounds (`(?<![A-Za-z0-9_])` / `(?![A-Za-z0-9_])`)
    so embedded Chinese characters don't break term boundaries — e.g.
    `用LSTM时` still matches `LSTM`.

    Longer terms match first (e.g. `6-axis geo` before `6-axis`) via
    length-descending sort, so the longer phrase is annotated as a unit.
    """
    if not glossary:
        return text
    terms = sorted(glossary.keys(), key=len, reverse=True)
    pattern = re.compile(
        "|".join(
            rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])"
            for t in terms
        )
    )
    seen: set[str] = set()
    out_parts: list[str] = []
    pos = 0
    for m in pattern.finditer(text):
        matched = m.group(0)
        if matched in seen:
            continue
        seen.add(matched)
        out_parts.append(text[pos:m.end()])
        out_parts.append(f"({glossary[matched]})")
        pos = m.end()
    out_parts.append(text[pos:])
    return "".join(out_parts)


# ---------- section formatters ----------


def _leaderboard_rows(
    claims: list[dict[str, Any]], *, top: int = 10
) -> list[str]:
    """Build the rows for the ``## Leaderboard`` section.

    Pulls claims with a structured ``metric`` block (R50 opt I) whose
    ``metric.kind`` indicates a performance number, sorts by
    ``metric.value`` descending, and formats one line per row. Returns
    an empty list when no claim carries a performance-kind metric —
    caller omits the whole section in that case.

    Kind filter (2026-05-19 audit, see [[CLM-0005]] deprecation note):
    strict opt-in. Only claims whose ``metric.kind`` is in
    ``PERFORMANCE_KINDS`` are shown. Hyperparameter / gap / ablation-impact /
    legacy-deprecated entries fall out automatically. Backfill ``kind:``
    on a claim's metric block to surface it.
    """
    PERFORMANCE_KINDS = {
        "performance",
        "performance-absolute",
        "performance-ratio",
        "performance-delta",
    }
    scored: list[tuple[float, dict[str, Any]]] = []
    for c in claims:
        m = c.get("metric")
        if not isinstance(m, dict):
            continue
        v = m.get("value")
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        kind = m.get("kind")
        if kind not in PERFORMANCE_KINDS:
            continue
        scored.append((float(v), c))
    scored.sort(key=lambda t: t[0], reverse=True)
    rows: list[str] = []
    for value, c in scored[:top]:
        cid = c.get("id", "?")
        name = (c.get("metric") or {}).get("name", "?")
        round_label = c.get("round", "?")
        rows.append(f"- {cid} [{round_label}] {name} = {value:.4f}")
    return rows


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
    glossary_path: Path | None = None,
) -> None:
    claims = _load_claims(claims_dir)
    questions = _load_questions(questions_dir)
    round_dirs = _iter_round_dirs(rounds_dir)
    glossary = _load_glossary(glossary_path) if glossary_path else {}

    # PI briefing layer (ADR-0003): newest R≥59 round whose verdict actually
    # carries a `## 给 PI 的话` section. Returns (round_dir, briefing_body)
    # or (None, None) if no R≥59 verdict has been written yet.
    pi_eligible = sorted(
        (d for d in round_dirs if _round_num(d) >= PI_BRIEFING_CUTOFF),
        key=_round_num,
    )
    latest_briefing_round: Path | None = None
    latest_briefing_body: str | None = None
    for d in reversed(pi_eligible):
        body = _extract_pi_briefing(_round_verdict_path(d))
        if body:
            latest_briefing_round = d
            latest_briefing_body = body
            break

    # Historical briefings: every R≥59 round older than the latest one,
    # one-line headline each, newest first, capped at HISTORICAL_BRIEFINGS_KEEP.
    historical_briefings: list[tuple[str, str]] = []
    if latest_briefing_round is not None:
        for d in reversed(pi_eligible):
            if d == latest_briefing_round:
                continue
            headline = _extract_pi_briefing_headline(_round_verdict_path(d))
            if headline:
                historical_briefings.append((d.name, headline))
                if len(historical_briefings) >= HISTORICAL_BRIEFINGS_KEEP:
                    break

    headlines = [
        c for c in claims
        if c.get("status") == "current" and "headline" in (c.get("tags") or [])
    ]

    # R166: state-aware grouping. Legacy plans without `state` field are
    # treated as if state=active (the backfill script sets state explicitly,
    # but render must not crash on rounds that pre-date the schema).
    active_rounds: list[Path] = []
    queued_rounds: list[Path] = []
    stale_rounds: list[Path] = []  # state=active AND opened ≥ 14 days
    for d in round_dirs:
        if not _round_is_in_flight(d):
            continue
        state = _round_state(d) or "active"
        if state == "queued":
            queued_rounds.append(d)
            continue
        if state != "active":
            # Terminal states (completed/superseded/aborted) with no
            # verdict.md (e.g. aborted) — silent; not in any in-flight list.
            continue
        opened_str = _round_opened(d)
        is_stale = False
        if opened_str:
            try:
                opened_date = dt.date.fromisoformat(opened_str.strip())
                age = (dt.date.today() - opened_date).days
                is_stale = age >= 14
            except ValueError:
                is_stale = False
        if is_stale:
            stale_rounds.append(d)
        else:
            active_rounds.append(d)

    # `completed_rounds` retains legacy meaning for "Latest Round": rounds
    # with verdict.md, regardless of declared state.
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

    # 0. (R≥59) PI briefing — top of file, before the agent-facing sections.
    # Omitted entirely until the first R≥59 verdict with a briefing exists.
    if latest_briefing_body and latest_briefing_round:
        lines.append(
            f"## 给 PI 的简报（最新一轮 — {latest_briefing_round.name}）"
        )
        lines.append("")
        annotated = _annotate_first_use(latest_briefing_body, glossary)
        lines.append(annotated)
        lines.append("")

    # 1. Headlines
    lines.append("## Headline Numbers")
    lines.append("")
    if headlines:
        lines.extend(_format_headline_line(c) for c in headlines)
    else:
        lines.append("(none)")
    lines.append("")

    # 2. In-Flight (state-aware split: 在跑 / 排队 / ⚠️ stale)
    def _fmt_round_line(d: Path) -> str:
        opened = _round_opened(d)
        suffix = f" [opened {opened}]" if opened else ""
        return f"- {d.name} — `memory/rounds/{d.name}/plan.md`{suffix}"

    lines.append("## 在跑 (state=active)")
    lines.append("")
    if active_rounds:
        lines.extend(_fmt_round_line(d) for d in active_rounds)
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("## 排队 (state=queued)")
    lines.append("")
    if queued_rounds:
        lines.extend(_fmt_round_line(d) for d in queued_rounds)
    else:
        lines.append("(none)")
    lines.append("")

    if stale_rounds:
        lines.append("## ⚠️ 疑似 stale (state=active, opened ≥ 14 days, no verdict)")
        lines.append("")
        lines.extend(_fmt_round_line(d) for d in stale_rounds)
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

    # 5b. Leaderboard (R50 opt H) — claims with structured ``metric`` field,
    # sorted by metric.value descending. Top 10 rows. Section is omitted
    # entirely when no claim carries a metric block (keeps STATE.md clean
    # for memories without metrics-style claims).
    lb_rows = _leaderboard_rows(claims, top=10)
    if lb_rows:
        lines.append("## Leaderboard (top-10 by metric)")
        lines.append("")
        for row in lb_rows:
            lines.append(row)
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

    # 7. (R≥59) Historical briefings — one-line headlines from past
    # R≥59 rounds (newest first). Omitted entirely until at least one
    # historical briefing exists.
    if historical_briefings:
        lines.append("## 历史简报")
        lines.append("")
        for round_name, headline in historical_briefings:
            lines.append(f"- {round_name}: {headline}")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render memory/STATE.md")
    base = Path(__file__).parent.parent
    parser.add_argument("--claims-dir", type=Path, default=base / "claims")
    parser.add_argument("--rounds-dir", type=Path, default=base / "rounds")
    parser.add_argument("--questions-dir", type=Path, default=base / "questions")
    parser.add_argument("--out", type=Path, default=base / "STATE.md")
    parser.add_argument(
        "--glossary",
        type=Path,
        default=base / "glossary.yml",
        help="path to glossary.yml for PI briefing first-use annotation",
    )
    args = parser.parse_args()
    render_state(
        args.claims_dir,
        args.rounds_dir,
        args.questions_dir,
        args.out,
        glossary_path=args.glossary,
    )
    print(f"Rendered {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
