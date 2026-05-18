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

# PI Briefing Layer (ADR-0003, R59 introduction).
# Verdicts from round R59 onward must include the PI briefing section.
# Pre-cutoff verdicts (R01..R58) are not retrofit — extracting the
# section from them in render.py would also yield nothing.
PI_BRIEFING_CUTOFF = 59
PI_BRIEFING_SECTION = "## 给 PI 的话"
PI_BRIEFING_LINE_CAP = 30  # soft-warn above this; does not block
PI_BRIEFING_BLOCK_RE = re.compile(
    rf"^{re.escape(PI_BRIEFING_SECTION)}\s*\n+(.*?)(?=\n##\s|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _load_entities(
    entity_dir: Path,
    *,
    glob_pattern: str,
    extras: dict[str, Any] | None = None,
    require_dir: bool = True,
) -> dict[str, dict[str, Any]]:
    """Load every frontmatter-tagged markdown file in ``entity_dir`` matching
    ``glob_pattern`` into a dict keyed by frontmatter ``id``.

    Used by both :func:`load_claims` and :func:`load_questions`. Centralises
    the frontmatter parse, the missing-``id`` guard, and the duplicate-id
    check so that adding a new entity kind in the future means writing a
    ≤5-line wrapper instead of duplicating ~20 lines.

    Args:
        entity_dir:    directory to scan.
        glob_pattern:  e.g. ``"CLM-*.md"`` or ``"Q-*.md"``.
        extras:        per-entity defaults to ``setdefault`` on each loaded
                       meta dict (e.g. ``superseded_by=[]``).
        require_dir:   if False and ``entity_dir`` does not exist, returns
                       ``{}`` silently (Q entity is optional).

    Raises:
        ValueError: missing frontmatter, missing ``id`` field, or duplicate id.
    """
    out: dict[str, dict[str, Any]] = {}
    if not entity_dir.exists():
        if require_dir:
            raise FileNotFoundError(f"entity dir does not exist: {entity_dir}")
        return out
    for path in sorted(entity_dir.glob(glob_pattern)):
        text = path.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(text)
        if not match:
            raise ValueError(f"{path.name}: no YAML frontmatter")
        meta = yaml.safe_load(match.group(1)) or {}
        meta["_path"] = path
        if extras:
            for k, v in extras.items():
                meta.setdefault(k, v)
        eid = meta.get("id")
        if not eid:
            raise ValueError(
                f"{path.name}: frontmatter missing required 'id' field"
            )
        if eid in out:
            raise ValueError(
                f"duplicate id {eid} in {path.name} and "
                f"{out[eid]['_path'].name}"
            )
        out[eid] = meta
    return out


def load_claims(claims_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every CLM-*.md frontmatter into a dict keyed by id."""
    return _load_entities(
        claims_dir,
        glob_pattern="CLM-*.md",
        extras={"superseded_by": [], "supersedes": []},
    )


def load_questions(questions_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every Q-*.md frontmatter into a dict keyed by id.

    Returns empty dict if ``questions_dir`` does not exist (Q entity is
    optional — a repo without any Q files is valid).
    """
    return _load_entities(
        questions_dir,
        glob_pattern="Q-*.md",
        require_dir=False,
    )


# ---------- Note entity (R-this-round addition) ----------

NOTE_SOURCE_ENUM = {
    "handoff",
    "eng-note",
    "adr-rationale",
    "legacy",
    "session-report",
}

NOTE_TOPIC_TOP_LEVEL = {
    "env",
    "training-infra",
    "evaluation",
    "agents",
    "scenarios",
    "paper",
    "memory-system",
    "pipeline",
}


def load_notes(notes_dir: Path) -> dict[str, dict[str, Any]]:
    """Load every NOTE-*.md frontmatter into a dict keyed by id.

    Returns empty dict if ``notes_dir`` does not exist (Note entity is
    optional — a repo without notes is valid).
    """
    return _load_entities(
        notes_dir,
        glob_pattern="NOTE-*.md",
        require_dir=False,
    )


def validate_note_rules(
    notes: dict[str, dict[str, Any]],
    claims: dict[str, dict[str, Any]],
    repo_root: Path,
) -> list[str]:
    """Five hard rules on Note entities. Returns list of error strings.

    N1: filename matches frontmatter ``id``
    N2: ``source`` ∈ NOTE_SOURCE_ENUM
    N3: ``source_path`` resolves to an existing file under ``repo_root``
    N4: every id in ``extracted_claims`` exists in ``claims``
    N5: ``topics[0]`` (top-level) ∈ NOTE_TOPIC_TOP_LEVEL
    """
    errors: list[str] = []
    for note in notes.values():
        nid = note["id"]

        # N1: filename ↔ id
        path: Path | None = note.get("_path")
        if path is not None and path.stem != nid:
            errors.append(
                f"{nid}: filename {path.name!r} does not match id"
            )

        # N2: source enum
        source = note.get("source")
        if source not in NOTE_SOURCE_ENUM:
            errors.append(
                f"{nid}: source {source!r} not in "
                f"{sorted(NOTE_SOURCE_ENUM)}"
            )

        # N3: source_path exists on disk
        src_path_raw = note.get("source_path")
        if not isinstance(src_path_raw, str) or not src_path_raw:
            errors.append(f"{nid}: source_path missing or empty")
        else:
            resolved = (repo_root / src_path_raw).resolve()
            if not resolved.exists():
                errors.append(
                    f"{nid}: source_path does not exist on disk: {src_path_raw}"
                )

        # N4: extracted_claims must reference existing claim ids
        for clm_id in note.get("extracted_claims", []) or []:
            if clm_id not in claims:
                errors.append(
                    f"{nid}: extracted_claims references {clm_id} which is not a known claim"
                )

        # N5: topics[0] in top-level whitelist
        topics = note.get("topics") or []
        if not topics:
            errors.append(f"{nid}: topics list is empty (need at least top-level)")
        else:
            top = topics[0]
            if top not in NOTE_TOPIC_TOP_LEVEL:
                errors.append(
                    f"{nid}: topics[0]={top!r} not a valid top-level "
                    f"(allowed: {sorted(NOTE_TOPIC_TOP_LEVEL)})"
                )

    return errors


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


def _round_num_from_verdict_path(verdict_path: Path) -> int | None:
    """Extract integer round number from a path like .../rounds/R59/verdict.md.

    Returns None if the parent directory doesn't match R\\d+ — caller then
    skips round-dependent checks (e.g. PI briefing cutoff).
    """
    m = ROUND_DIR_RE.match(verdict_path.parent.name)
    return int(m.group(1)) if m else None


def validate_verdict_structure(verdict_path: Path) -> list[str]:
    """Round verdict must have the 3 mandatory Q-section H2s, plus — for
    R≥59 (ADR-0003) — the `## 给 PI 的话` PI briefing section.

    Historical verdicts (R01..R38) use varied Status header text and not all
    have explicit TL;DR — those checks live in the warnings path, not here.
    Pre-R59 verdicts are not retrofit for the briefing requirement.
    """
    errors: list[str] = []
    if not verdict_path.exists():
        return errors  # verdict.md absent = round in-flight, not an error
    text = verdict_path.read_text(encoding="utf-8")
    for section in VERDICT_REQUIRED_SECTIONS:
        if section not in text:
            errors.append(f"{verdict_path}: missing section '{section}'")
    round_num = _round_num_from_verdict_path(verdict_path)
    if round_num is not None and round_num >= PI_BRIEFING_CUTOFF:
        if PI_BRIEFING_SECTION not in text:
            errors.append(
                f"{verdict_path}: missing section '{PI_BRIEFING_SECTION}' "
                f"(mandatory from R{PI_BRIEFING_CUTOFF} onward — see ADR-0003)"
            )
    return errors


def warn_verdict_recommended(verdict_path: Path) -> list[str]:
    """Soft checks: TL;DR + Status header + (R≥59) PI briefing length cap.

    Returns warning strings (not errors). Briefing length is checked only
    for R≥59 since pre-cutoff verdicts have no briefing section.
    """
    warnings: list[str] = []
    if not verdict_path.exists():
        return warnings
    text = verdict_path.read_text(encoding="utf-8")
    for section in VERDICT_RECOMMENDED_SECTIONS:
        if section not in text:
            warnings.append(f"{verdict_path}: missing recommended section '{section}'")
    if not VERDICT_STATUS_HEADER_RE.search(text):
        warnings.append(f"{verdict_path}: missing '**Status**:' header line")
    round_num = _round_num_from_verdict_path(verdict_path)
    if round_num is not None and round_num >= PI_BRIEFING_CUTOFF:
        warnings.extend(_warn_pi_briefing_length(verdict_path, text))
    return warnings


def _warn_pi_briefing_length(verdict_path: Path, text: str) -> list[str]:
    """Soft cap on `## 给 PI 的话` body length (non-blank lines only).

    The user explicitly asked for brevity ("要简洁"). 30 lines is the
    soft ceiling; verdicts exceeding it get a warning but still pass.
    Promote to hard ERROR after 5+ rounds of consistent discipline.
    """
    match = PI_BRIEFING_BLOCK_RE.search(text)
    if not match:
        return []  # absence already errored in validate_verdict_structure
    body = match.group(1).strip()
    non_blank = [ln for ln in body.splitlines() if ln.strip()]
    if len(non_blank) > PI_BRIEFING_LINE_CAP:
        return [
            f"{verdict_path}: 给 PI 的话 is {len(non_blank)} non-blank lines, "
            f"recommended ≤ {PI_BRIEFING_LINE_CAP} (要简洁 — see ADR-0003)"
        ]
    return []


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

    # Rule 6 (R50 opt J): ``status: obsoleted`` requires obsoleted_round
    # and obsoleted_reason so the obsoletion is auditable. Distinct from
    # ``status: superseded`` (which always points at a successor claim);
    # ``obsoleted`` is for claims whose number / decision became stale due
    # to external change (ranker drift, env-semantics shift) without a
    # replacement claim. Example: CLM-0008's R30 ranker baseline 0.104
    # was rendered stale by R36 ranker tuning to 0.094.
    for claim in claims.values():
        if claim.get("status") != "obsoleted":
            continue
        if not claim.get("obsoleted_round"):
            errors.append(
                f"{claim['id']}: status=obsoleted requires 'obsoleted_round' field"
            )
        if not claim.get("obsoleted_reason"):
            errors.append(
                f"{claim['id']}: status=obsoleted requires 'obsoleted_reason' field"
            )

    # Rule 5 (R50 opt I): structured ``metric`` field, if present, must
    # carry ``name: str`` and a numeric ``value`` so STATE.md's
    # leaderboard (H) can sort + display deterministically.
    for claim in claims.values():
        metric = claim.get("metric")
        if metric is None:
            continue
        if not isinstance(metric, dict):
            errors.append(
                f"{claim['id']}: metric field must be a mapping "
                f"(got {type(metric).__name__})"
            )
            continue
        if "name" not in metric:
            errors.append(f"{claim['id']}: metric block missing 'name' key")
        elif not isinstance(metric["name"], str) or not metric["name"]:
            errors.append(
                f"{claim['id']}: metric.name must be a non-empty string"
            )
        if "value" not in metric:
            errors.append(f"{claim['id']}: metric block missing 'value' key")
        else:
            v = metric["value"]
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                errors.append(
                    f"{claim['id']}: metric.value must be numeric "
                    f"(got {type(v).__name__})"
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

    # Warning C (R53 patch A2): finding / correction claims whose statement
    # cites a benchmark-like decimal number but carry no metric block. Pushes
    # adoption of R50 opt I (structured metric) without blocking authorship.
    # Decision claims are exempt — they are choices, not measurements.
    for claim in claims.values():
        ctype = claim.get("type")
        if ctype not in ("finding", "correction"):
            continue
        if claim.get("metric"):
            continue
        stmt = claim.get("statement") or ""
        if _DECIMAL_RE.search(stmt):
            warnings.append(
                f"{claim['id']}: statement cites decimal(s) but has no "
                f"metric block — consider adding one for H/L (soft hint)"
            )

    return errors, warnings


# Module-level regex for the soft metric-hint check (Warning C).
# Matches a decimal with at least two fractional digits — captures the
# benchmark form (e.g. 0.444, 0.3346) while skipping single-digit
# decimals like "+0.1" (mostly used in ranges / step sizes).
_DECIMAL_RE = re.compile(r"\b\d+\.\d{2,4}\b")


def _is_pattern_provenance(p: str) -> bool:
    """A provenance entry is treated as a pattern (skipped by the soft
    path check) if it contains glob wildcards or brace expansion.

    Examples that count as patterns:
        results/td3_norm_s{49,50,51}/agent_*_best.pt
        logs/r46_beta_s{49,50,51}.log
        memory/claims/CLM-00{40..47}.md  # range expansion

    Examples that count as literal paths:
        results/research_loop/r48_alpha_h256_sweep.json
        scripts/_r44_eval_no_control_g4preserved.py
        memory/rounds/R48/verdict.md
    """
    return any(ch in p for ch in "*?[{")


def check_provenance_paths(
    claims: dict[str, dict[str, Any]], *, repo_root: Path
) -> list[str]:
    """Soft check: for each claim's provenance entries that look like
    literal paths (no glob / brace patterns), warn if the path doesn't
    resolve under ``repo_root``.

    Always returns warnings, never errors. The check is soft because
    ``results/*`` is gitignored — cross-session provenance is routinely
    dangling and that's intentional (results are reproducible from the
    listed scripts). Pre-R50, audits had to grep manually.

    R50 optimization K.
    """
    out: list[str] = []
    for claim in claims.values():
        for entry in claim.get("provenance", []) or []:
            if not isinstance(entry, str):
                continue
            head = _extract_provenance_path(entry)
            if not head:
                continue
            if _is_pattern_provenance(head):
                continue
            full = (repo_root / head).resolve()
            if not full.exists():
                out.append(
                    f"{claim['id']}: provenance path missing on disk: {head}"
                )
    return out


def _extract_provenance_path(entry: str) -> str:
    """Pull the literal path prefix out of a provenance entry.

    Provenance lines commonly carry trailing markers:
      ``path/to/file.py (commentary)``      → strip "(commentary)"
      ``path/main.tex §IV-C "section"``      → strip "§..."
      ``path/file.py @ refactor/branch``    → strip "@ gitref"
      ``path/file.py @abc123``              → strip "@abc123"

    Returns the path portion only (stripped of whitespace).
    """
    p = entry
    # Cut at the first of: "(", " §", " @", "  " (double-space comment).
    for sep in ("(", " §", "§", " @"):
        idx = p.find(sep)
        if idx != -1:
            p = p[:idx]
    return p.strip()


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
    parser.add_argument("--notes-dir", type=Path, default=base / "notes",
                        help="path to memory/notes/")
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

    repo_root = Path(__file__).resolve().parents[2]
    notes = load_notes(args.notes_dir)
    n_errors = validate_note_rules(notes, claims, repo_root=repo_root)
    errors.extend(n_errors)

    if not args.skip_verdicts:
        for verdict_path in _iter_verdicts(args.rounds_dir):
            errors.extend(validate_verdict_structure(verdict_path))
            warnings.extend(warn_verdict_recommended(verdict_path))

    # R50 opt K: soft check that provenance paths exist on disk.
    # Gitignored areas (results/, logs/) routinely produce warnings;
    # users skim past them. Never blocks validation.
    warnings.extend(check_provenance_paths(claims, repo_root=repo_root))

    for w in warnings:
        print(f"WARN: {w}")
    for e in errors:
        print(f"ERROR: {e}", file=sys.stderr)
    if errors:
        return 1
    print(
        f"OK: {len(claims)} claims, {len(questions)} questions, "
        f"{len(notes)} notes, {len(warnings)} warnings"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
