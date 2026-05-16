"""Claim + Question ledger validator. Hard rules + soft warnings."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# Strict round-directory pattern. Shared with render.py so both tools agree
# on what counts as a "round" dir under memory/rounds/. README/, _SKIPPED.md,
# R-legacy/ etc. are intentionally excluded.
ROUND_DIR_RE = re.compile(r"^R(\d+)$")

QUESTION_STATUS_ENUM = {
    "open",
    "in-flight",
    "closed-positive",
    "closed-negative",
    "abandoned",
}

VERDICT_REQUIRED_SECTIONS = (
    "## Questions opened",
    "## Questions closed",
    "## Questions advanced",
)
# Soft (warning-only) checks — historical verdicts use varied Status text
# (COMPLETE / DONE / INCONCLUSIVE / PARTIAL / etc.) and not all have TL;DR.
# Forward template (_TEMPLATE_VERDICT.md) includes them; legacy verdicts
# are not retrofit-mandated.
VERDICT_RECOMMENDED_SECTIONS = ("## TL;DR",)
VERDICT_STATUS_HEADER_RE = re.compile(r"^\*\*Status\*\*\s*:", re.MULTILINE)


def load_claims(claims_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every CLM-*.md frontmatter into a dict keyed by id."""
    claims: dict[str, dict[str, Any]] = {}
    for path in sorted(claims_dir.glob("CLM-*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path.name}: no YAML frontmatter")
        meta = yaml.safe_load(match.group(1)) or {}
        meta["_path"] = path
        meta.setdefault("superseded_by", [])
        meta.setdefault("supersedes", [])
        cid = meta.get("id")
        if not cid:
            raise ValueError(
                f"{path.name}: frontmatter missing required 'id' field"
            )
        if cid in claims:
            raise ValueError(
                f"duplicate id {cid} in {path.name} and "
                f"{claims[cid]['_path'].name}"
            )
        claims[cid] = meta
    return claims


def load_questions(questions_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every Q-*.md frontmatter into a dict keyed by id.

    Returns empty dict if questions_dir doesn't exist (Q entity is optional —
    a repo without any Q files is valid)."""
    questions: dict[str, dict[str, Any]] = {}
    if not questions_dir.exists():
        return questions
    for path in sorted(questions_dir.glob("Q-*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path.name}: no YAML frontmatter")
        meta = yaml.safe_load(match.group(1)) or {}
        meta["_path"] = path
        qid = meta.get("id")
        if not qid:
            raise ValueError(
                f"{path.name}: frontmatter missing required 'id' field"
            )
        if qid in questions:
            raise ValueError(
                f"duplicate id {qid} in {path.name} and "
                f"{questions[qid]['_path'].name}"
            )
        questions[qid] = meta
    return questions


def validate_question_rules(
    questions: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
    rounds_dir: Path,
) -> list[str]:
    """Three hard rules on Q entities. Returns list of error strings."""
    errors: list[str] = []
    for q in questions.values():
        qid = q["id"]
        status = q.get("status")

        # Rule Q1: status must be in enum
        if status not in QUESTION_STATUS_ENUM:
            errors.append(
                f"{qid}: status '{status}' not in "
                f"{sorted(QUESTION_STATUS_ENUM)}"
            )
            continue  # downstream checks meaningless if status invalid

        # Rule Q2: closed-* must have closed_round + closed_by
        if status.startswith("closed-"):
            closed_round = q.get("closed_round")
            closed_by = q.get("closed_by")
            if not closed_round or not closed_by:
                errors.append(
                    f"{qid}: status={status} but missing "
                    f"closed_round/closed_by"
                )
            elif not isinstance(closed_by, str):
                # Schema is one closing claim per Q. A list (or any non-string)
                # is rejected here rather than crashing inside the dict lookup.
                errors.append(
                    f"{qid}: closed_by must be a single CLM-id string, "
                    f"got {type(closed_by).__name__}: {closed_by!r}"
                )
            else:
                if not (rounds_dir / closed_round).exists():
                    errors.append(
                        f"{qid}: closed_round {closed_round} dir does not exist"
                    )
                if closed_by not in claims:
                    errors.append(
                        f"{qid}: closed_by {closed_by} not a known claim id"
                    )

        # Rule Q3: opened_round must exist
        opened_round = q.get("opened_round")
        if not opened_round:
            errors.append(f"{qid}: missing opened_round")
        elif not (rounds_dir / opened_round).exists():
            errors.append(
                f"{qid}: opened_round {opened_round} dir does not exist"
            )

    return errors


def validate_verdict_structure(verdict_path: Path) -> list[str]:
    """Round verdict must have the 3 mandatory Q-section H2s.

    Historical verdicts (R01..R38) use varied Status header text and not all
    have explicit TL;DR — those checks live in the warnings path, not here.
    """
    errors: list[str] = []
    if not verdict_path.exists():
        return errors  # verdict.md absent = round in-flight, not an error
    text = verdict_path.read_text(encoding="utf-8")
    for section in VERDICT_REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"{verdict_path}: missing section '{section}'")
    return errors


def warn_verdict_recommended(verdict_path: Path) -> list[str]:
    """Soft checks: TL;DR + Status header. Returns warning strings (not errors)."""
    warnings: list[str] = []
    if not verdict_path.exists():
        return warnings
    text = verdict_path.read_text(encoding="utf-8")
    for section in VERDICT_RECOMMENDED_SECTIONS:
        if section not in text:
            warnings.append(f"{verdict_path}: missing recommended section '{section}'")
    if not VERDICT_STATUS_HEADER_RE.search(text):
        warnings.append(f"{verdict_path}: missing '**Status**:' header line")
    return warnings


def validate_rules(claims: dict[str, dict[str, Any]]) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Hard rules go to errors; soft checks to warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    # Rule 1: id uniqueness — guards against same id value appearing under different
    # dict keys (possible when validate_rules is called outside the main() flow).
    seen_ids: dict[str, str] = {}
    for key, claim in claims.items():
        cid = claim["id"]
        if cid in seen_ids and seen_ids[cid] != key:
            errors.append(f"duplicate id {cid} in key {key} and key {seen_ids[cid]}")
        seen_ids[cid] = key

    # Rule 2: supersedes target must exist
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                errors.append(
                    f"{claim['id']}.supersedes references {target} which does not exist"
                )

    # Rule 3: status: current ↔ superseded_by must be empty
    for claim in claims.values():
        if claim.get("status") == "current" and claim.get("superseded_by"):
            errors.append(
                f"{claim['id']} has status: current but non-empty "
                f"superseded_by: {claim['superseded_by']}"
            )

    # Rule 4: trust ↔ type consistency.
    # Decisions are choices — they cannot be "Verified" (V); they are Stated (S).
    # Corrections replace a prior verified number — the replacement must itself
    # be Verified (V), not Stated. Findings remain flexible (V / S / T).
    for claim in claims.values():
        ctype = claim.get("type")
        ctrust = claim.get("trust")
        if ctype == "decision" and ctrust != "S":
            errors.append(
                f"{claim['id']}: decision claims must have trust: S "
                f"(got trust: {ctrust})"
            )
        if ctype == "correction" and ctrust != "V":
            errors.append(
                f"{claim['id']}: correction claims must have trust: V "
                f"(got trust: {ctrust})"
            )

    # Warning A: forward/back edge symmetry
    for claim in claims.values():
        for target in claim.get("supersedes", []) or []:
            if target not in claims:
                continue
            back = claims[target].get("superseded_by", []) or []
            if claim["id"] not in back:
                warnings.append(
                    f"asymmetric edge: {claim['id']}.supersedes lists {target}, "
                    f"but {target}.superseded_by missing {claim['id']}"
                )

    # Warning B: trust: V requires non-empty provenance
    for claim in claims.values():
        if claim.get("trust") == "V" and not claim.get("provenance"):
            warnings.append(f"{claim['id']} has trust: V but empty provenance")

    return errors, warnings


def _rewrite_frontmatter(path: Path, updates: dict[str, Any]) -> None:
    """Rewrite the YAML block of a claim file, preserving body and key order
    where possible."""
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(text)
    if not match:
        raise ValueError(f"{path.name}: no frontmatter to rewrite")
    meta = yaml.safe_load(match.group(1)) or {}
    meta.update(updates)
    new_block = yaml.safe_dump(
        meta, sort_keys=False, allow_unicode=True, default_flow_style=False
    ).strip()
    body = text[match.end():]
    path.write_text(f"---\n{new_block}\n---\n{body}", encoding="utf-8")


def fix_back_edges(claims: dict[str, dict[str, Any]], *, write: bool) -> list[str]:
    """For every X with supersedes: [Y, ...], ensure Y.superseded_by includes X
    and Y.status == 'superseded'. Returns list of changes made."""
    changes: list[str] = []
    for claim in claims.values():
        for target_id in claim.get("supersedes", []) or []:
            target = claims.get(target_id)
            if target is None:
                continue
            back = list(target.get("superseded_by", []) or [])
            need_back = claim["id"] not in back
            need_status = target.get("status") != "superseded"
            if not (need_back or need_status):
                continue
            if need_back:
                back.append(claim["id"])
            updates = {"superseded_by": back, "status": "superseded"}
            changes.append(
                f"{target_id}: superseded_by += {claim['id']}, status -> superseded"
            )
            if write:
                _rewrite_frontmatter(target["_path"], updates)
                target.update(updates)
    return changes


def _iter_verdicts(rounds_dir: Path):
    """Yield Path objects for every round-verdict file to be validated.

    Canonical-preempt semantics (matches `render.py`):
    - If `RNN/verdict.md` exists, yield only it. Sibling `*verdict*.md`
      files are then treated as supplementary notes (cross-round summaries,
      audit verdicts, etc.) and are NOT validated as per-round verdicts.
    - Otherwise yield every `*verdict*.md` in the directory.

    Directory filter is strict: only `R\\d+` dirs are considered. This is
    intentionally tighter than `startswith("R")` so directories like
    `README`, `R-legacy`, or `R_archive` cannot leak in.
    """
    if not rounds_dir.exists():
        return
    for round_dir in sorted(rounds_dir.iterdir()):
        if not round_dir.is_dir() or not ROUND_DIR_RE.match(round_dir.name):
            continue
        canonical = round_dir / "verdict.md"
        if canonical.exists():
            yield canonical
            continue
        for alt in sorted(round_dir.glob("*verdict*.md")):
            yield alt


def main() -> int:
    parser = argparse.ArgumentParser(description="Claim + Question ledger validator")
    base = Path(__file__).parent.parent
    parser.add_argument("--claims-dir", type=Path, default=base / "claims",
                        help="path to memory/claims/")
    parser.add_argument("--questions-dir", type=Path, default=base / "questions",
                        help="path to memory/questions/")
    parser.add_argument("--rounds-dir", type=Path, default=base / "rounds",
                        help="path to memory/rounds/")
    parser.add_argument("--fix", action="store_true",
                        help="auto-write missing back edges and flip status")
    parser.add_argument("--skip-verdicts", action="store_true",
                        help="skip verdict structure validation (useful before retrofit)")
    args = parser.parse_args()

    claims = load_claims(args.claims_dir)
    if args.fix:
        changes = fix_back_edges(claims, write=True)
        for c in changes:
            print(f"FIX: {c}")
        # reload after writing
        claims = load_claims(args.claims_dir)

    errors, warnings = validate_rules(claims)
    questions = load_questions(args.questions_dir)
    q_errors = validate_question_rules(questions, claims, args.rounds_dir)
    errors.extend(q_errors)

    if not args.skip_verdicts:
        for verdict_path in _iter_verdicts(args.rounds_dir):
            errors.extend(validate_verdict_structure(verdict_path))
            warnings.extend(warn_verdict_recommended(verdict_path))

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        return 1
    print(
        f"OK: {len(claims)} claims, {len(questions)} questions, "
        f"{len(warnings)} warnings"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
