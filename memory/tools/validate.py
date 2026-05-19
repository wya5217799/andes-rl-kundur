"""Claim + Question ledger validator. Hard rules + soft warnings."""
from __future__ import annotations
import argparse
import re
import sys
from datetime import date, datetime
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

# R166: round lifecycle state machine.
# `state` on RNNN/plan.md frontmatter is the canonical source of truth for
# whether a round is active, queued, completed, superseded, or aborted.
# See ADR-0003 + R166 plan.md.
ROUND_STATE_ENUM = {"active", "queued", "completed", "superseded", "aborted"}
ROUND_STATE_TERMINAL = {"completed", "superseded", "aborted"}
ROUND_STALE_ACTIVE_DAYS = 14
ROUND_STALE_QUEUED_DAYS = 7


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


def _parse_iso_date(value: Any) -> date | None:
    """Coerce a YAML date / datetime / 'YYYY-MM-DD' string to a date."""
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _load_plan_frontmatter(plan_path: Path) -> dict[str, Any] | None:
    """Return parsed frontmatter dict, or None if the file/frontmatter is absent."""
    if not plan_path.exists():
        return None
    text = plan_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}


def validate_round_state(
    plan_path: Path,
    *,
    rounds_dir: Path | None = None,
    today: date | None = None,
) -> tuple[list[str], list[str]]:
    """Validate the `state` field on a round's plan.md frontmatter.

    Hard rules (errors):
    - R-state-required: plan.md must have a `state` field
    - R-state-enum: state ∈ {active, queued, completed, superseded, aborted}
    - R-terminal-fields:
        * completed → sibling verdict.md must exist
        * superseded → `superseded_by_round` non-null AND target dir exists
        * aborted   → `abort_reason` non-null

    Soft rules (warnings):
    - R-stale-active: state=active + opened ≥ 14 days ago + no verdict
    - R-stale-queued: state=queued + opened ≥ 7 days ago

    Terminal states never trigger stale warnings.

    Args:
        plan_path:   path to memory/rounds/RNNN/plan.md
        rounds_dir:  parent dir for cross-round lookups (superseded_by_round
                     target existence). Defaults to plan_path.parent.parent.
        today:       overridable date for staleness arithmetic (tests inject).

    Returns:
        (errors, warnings) — both lists of strings, callers append to their
        own buckets. Mirrors :func:`validate_rules`.
    """
    errors: list[str] = []
    warnings: list[str] = []

    fm = _load_plan_frontmatter(plan_path)
    if fm is None:
        # No frontmatter is not itself an error (some legacy plans are pure
        # markdown), but state cannot be derived — emit one error.
        errors.append(
            f"{plan_path}: plan.md missing YAML frontmatter; "
            f"`state` field is required (R-state-required)"
        )
        return errors, warnings

    state = fm.get("state")
    if state is None:
        errors.append(
            f"{plan_path}: `state` field is required (R-state-required); "
            f"add one of {sorted(ROUND_STATE_ENUM)}"
        )
        return errors, warnings

    if state not in ROUND_STATE_ENUM:
        errors.append(
            f"{plan_path}: invalid state {state!r} "
            f"(R-state-enum; must be one of {sorted(ROUND_STATE_ENUM)})"
        )
        return errors, warnings

    round_dir = plan_path.parent
    parent_dir = rounds_dir if rounds_dir is not None else round_dir.parent

    if state == "completed":
        verdict = round_dir / "verdict.md"
        if not verdict.exists():
            errors.append(
                f"{plan_path}: state=completed requires sibling verdict.md "
                f"(R-terminal-fields)"
            )

    if state == "superseded":
        target = fm.get("superseded_by_round")
        if not target:
            errors.append(
                f"{plan_path}: state=superseded requires `superseded_by_round` "
                f"field (R-terminal-fields)"
            )
        else:
            target_dir = parent_dir / str(target)
            if not target_dir.is_dir():
                errors.append(
                    f"{plan_path}: superseded_by_round target {target!r} "
                    f"does not exist at {target_dir} (R-terminal-fields)"
                )

    if state == "aborted":
        reason = fm.get("abort_reason")
        if not reason:
            errors.append(
                f"{plan_path}: state=aborted requires `abort_reason` field "
                f"(R-terminal-fields)"
            )

    if state in ROUND_STATE_TERMINAL:
        # Terminal states do not produce staleness warnings.
        return errors, warnings

    # Staleness — only for active / queued.
    today = today or date.today()
    opened = _parse_iso_date(fm.get("opened"))
    if opened is None:
        # Missing `opened` is a soft signal — can't compute age, but the
        # state-required hard rule already passed. Warn so we can backfill.
        warnings.append(
            f"{plan_path}: state={state} but `opened` is missing/unparseable; "
            f"cannot check staleness"
        )
        return errors, warnings

    age_days = (today - opened).days
    if state == "active" and age_days >= ROUND_STALE_ACTIVE_DAYS:
        verdict = round_dir / "verdict.md"
        if not verdict.exists():
            warnings.append(
                f"{plan_path}: {round_dir.name} stale-active "
                f"({age_days}d old, no verdict.md) — confirm still in progress "
                f"or flip state to completed/superseded/aborted (R-stale-active)"
            )
    if state == "queued" and age_days >= ROUND_STALE_QUEUED_DAYS:
        warnings.append(
            f"{plan_path}: {round_dir.name} queued {age_days}d without firing; "
            f"likely abort candidate (R-stale-queued)"
        )

    return errors, warnings


def validate_rules(
    claims: dict[str, dict[str, Any]],
    *,
    questions: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Hard rules go to errors; soft checks to warnings.

    ``questions`` is optional (legacy callers may not pass it); when provided,
    enables Rule 7 (closes_question bidirectional consistency, F3 from
    2026-05-19 flow audit).
    """
    errors: list[str] = []
    warnings: list[str] = []
    questions = questions or {}

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

    # Rule 5b (F5 from 2026-05-19 flow audit): for claims emitted in round
    # R115 or later, ``metric.kind`` becomes mandatory so STATE.md's
    # leaderboard never silently re-pollutes with hyper / gap / structural
    # values. Pre-R115 claims are grandfathered (no kind defaults to
    # excluded by render.py's strict opt-in filter).
    METRIC_KIND_MANDATORY_FROM = 115
    for claim in claims.values():
        metric = claim.get("metric")
        if not isinstance(metric, dict):
            continue
        round_num = _claim_round_num(claim)
        if round_num is None or round_num < METRIC_KIND_MANDATORY_FROM:
            continue
        if not metric.get("kind"):
            errors.append(
                f"{claim['id']} (R{round_num}): metric.kind required for "
                f"claims emitted from R{METRIC_KIND_MANDATORY_FROM} onward "
                f"(F5 audit 2026-05-19) — pick one of "
                f"{sorted(METRIC_KIND_ENUM)}"
            )
        elif metric["kind"] not in METRIC_KIND_ENUM:
            errors.append(
                f"{claim['id']}: metric.kind={metric['kind']!r} not in "
                f"allowed set {sorted(METRIC_KIND_ENUM)}"
            )

    # Rule 7 (F3 from 2026-05-19 flow audit): closes_question bidirectional
    # check. If a claim declares it closes a question, that question must
    # exist, be in a closed-* status, and point back at the closing claim
    # via closed_by. This catches the "CLM emitted but Q stays open"
    # staleness pattern that caused Q-0022/0024/0025 to dangle this session.
    for claim in claims.values():
        closes = claim.get("closes_question") or []
        if isinstance(closes, str):
            closes = [closes]
        for qid in closes:
            if not isinstance(qid, str) or not qid:
                continue
            q = questions.get(qid)
            if q is None:
                errors.append(
                    f"{claim['id']}.closes_question references {qid} "
                    f"which does not exist"
                )
                continue
            qstatus = q.get("status") or ""
            if not qstatus.startswith("closed-"):
                errors.append(
                    f"{claim['id']}.closes_question references {qid} "
                    f"but {qid}.status={qstatus!r} (must be closed-*)"
                )
            closed_by = q.get("closed_by")
            if closed_by != claim["id"]:
                errors.append(
                    f"{claim['id']}.closes_question references {qid} "
                    f"but {qid}.closed_by={closed_by!r} "
                    f"(must equal {claim['id']!r})"
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

    # Warning D (F2 from 2026-05-19 flow audit): caveat-lineage check.
    # If a claim's provenance cites a sister claim tagged `caveat-needed`,
    # the citing claim's statement should carry caveat-language too
    # (Caveat:/caveat:/limitation:/synthetic obs/on-manifold etc.). This
    # catches the "downstream claim drops upstream caveat" drift pattern
    # observed CLM-0183 → CLM-0193 → CLM-0207 in this session's audit.
    for claim in claims.values():
        cited_caveat_parents = _cited_caveat_parents(claim, claims)
        if not cited_caveat_parents:
            continue
        stmt = (claim.get("statement") or "").lower()
        if _CAVEAT_RE.search(stmt):
            continue
        warnings.append(
            f"{claim['id']}: cites caveat-needed parent(s) "
            f"{sorted(cited_caveat_parents)} but statement contains no "
            f"caveat / limitation language — propagate the upstream caveat"
        )

    return errors, warnings


# Module-level regex for the soft metric-hint check (Warning C).
# Matches a decimal with at least two fractional digits — captures the
# benchmark form (e.g. 0.444, 0.3346) while skipping single-digit
# decimals like "+0.1" (mostly used in ranges / step sizes).
_DECIMAL_RE = re.compile(r"\b\d+\.\d{2,4}\b")

# Allowed values for ``metric.kind`` (Rule 5b, F5 from 2026-05-19 audit).
# Performance kinds surface on STATE.md leaderboard via render.py's strict
# opt-in filter; non-performance kinds stay in the ledger but don't pollute
# the leaderboard. Keep this enum in sync with
# memory/tools/render.py::PERFORMANCE_KINDS.
METRIC_KIND_ENUM = {
    # Performance-shaped (surface on leaderboard):
    "performance",
    "performance-absolute",
    "performance-ratio",
    "performance-delta",
    "performance-legacy",  # for deprecated-ranker numbers like CLM-0005/6/7
    # Non-performance shaped (kept in ledger, hidden from leaderboard):
    "hyper",
    "gap",
    "ablation-impact-pct",
    "structural",
    "count",
    "rate",
    "correlation",
}

# Caveat-detection regex (Warning D, F2 from 2026-05-19 audit). Matches a
# range of caveat / limitation phrasings used historically in this project,
# in both English and Chinese (per project caveman-cn convention).
_CAVEAT_RE = re.compile(
    r"caveat|limitation|caveats|on-manifold|off-manifold|synthetic obs|"
    r"single seed|n=1|未验|未验证|未上 env|未 on-policy|脚注|"
    r"refute|refuted|refutation|saturation deficit only on|"
    r"out-of-distribution|ood",
    re.IGNORECASE,
)


def _claim_round_num(claim: dict[str, Any]) -> int | None:
    """Best-effort parse of the claim's round field (e.g. 'R115' → 115)."""
    rd = claim.get("round")
    if not isinstance(rd, str):
        return None
    m = re.match(r"R(\d+)$", rd)
    return int(m.group(1)) if m else None


def _cited_caveat_parents(
    claim: dict[str, Any], claims: dict[str, dict[str, Any]]
) -> set[str]:
    """Return the set of caveat-needed parent claim IDs cited in
    ``claim``'s provenance. A claim is considered caveat-needed iff it
    carries the literal tag ``caveat-needed`` in its ``tags`` list.

    Only direct provenance citations count (we do not transitively walk
    the lineage); the goal is to surface drop-points, not the full
    transitive closure of caveats.
    """
    cited: set[str] = set()
    prov = claim.get("provenance") or []
    if not isinstance(prov, list):
        return cited
    for entry in prov:
        if not isinstance(entry, str):
            continue
        # Match "memory/claims/CLM-NNNN.md" or bare "CLM-NNNN" tokens.
        for m in re.finditer(r"\bCLM-\d{4}\b", entry):
            parent_id = m.group(0)
            if parent_id == claim["id"]:
                continue
            parent = claims.get(parent_id)
            if parent is None:
                continue
            tags = parent.get("tags") or []
            if "caveat-needed" in tags:
                cited.add(parent_id)
    return cited


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
        # F7 (2026-05-19 audit): per-claim opt-out for legacy claims whose
        # provenance points to _archive/ or _legacy/ scripts that have been
        # intentionally moved out. Set ``archived_provenance: true`` in the
        # claim's frontmatter to silence missing-path warnings for this claim.
        if claim.get("archived_provenance") is True:
            continue
        for entry in claim.get("provenance", []) or []:
            if not isinstance(entry, str):
                continue
            head = _extract_provenance_path(entry)
            if not head:
                continue
            if _is_pattern_provenance(head):
                continue
            # Implicit archive marker: any path under _archive/ or _legacy/
            # is considered intentionally non-existent (claims may reference
            # historical scripts moved to those locations).
            if head.startswith(("_archive/", "_legacy/", "memory/handoffs/")):
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
      ``path/file.py:242``                  → strip ":lineno" (F7 audit)
      ``path/file.py::symbol``              → strip "::symbol" (F7 audit)
      ``path/dir/ + extra.json``            → strip " + extra"  (F7 audit)

    Heuristic for ``:`` is "first colon AFTER the last slash", so URL-like
    ``http://host/path`` strings (no slash after the colon) are not mauled.

    Returns the path portion only (stripped of whitespace).
    """
    p = entry
    # Cut at the first of: "(", " §", " @", " + " (continuation marker).
    for sep in ("(", " §", "§", " @", " + "):
        idx = p.find(sep)
        if idx != -1:
            p = p[:idx]
    p = p.strip()
    # Strip ``::symbol`` (Python-style attribute) — always safe.
    sym_idx = p.find("::")
    if sym_idx != -1:
        p = p[:sym_idx]
    # Strip trailing ``:lineno`` only if there's a slash earlier (filters out
    # URL schemes). Lineno is purely digits after the colon.
    last_slash = p.rfind("/")
    last_colon = p.rfind(":")
    if (
        last_colon > last_slash
        and last_colon != -1
        and p[last_colon + 1:].isdigit()
    ):
        p = p[:last_colon]
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

    questions = load_questions(args.questions_dir)
    errors, warnings = validate_rules(claims, questions=questions)
    q_errors = validate_question_rules(questions, claims, args.rounds_dir)
    errors.extend(q_errors)

    if not args.skip_verdicts:
        for verdict_path in _iter_verdicts(args.rounds_dir):
            errors.extend(validate_verdict_structure(verdict_path))
            warnings.extend(warn_verdict_recommended(verdict_path))

    # R166: round lifecycle state check on every RNNN/plan.md.
    for round_dir in sorted(args.rounds_dir.iterdir()):
        if not round_dir.is_dir() or not ROUND_DIR_RE.match(round_dir.name):
            continue
        plan_path = round_dir / "plan.md"
        if not plan_path.exists():
            # No plan.md. Two sub-cases:
            #   (a) some verdict*.md exists → legacy/parallel verdict-only
            #       convention; effectively closed, no warning.
            #   (b) truly empty → reserved-but-abandoned zombie.
            has_verdict = any(round_dir.glob("*verdict*.md"))
            if not has_verdict:
                warnings.append(
                    f"{round_dir}: reserved but no plan.md and no verdict "
                    f"(zombie; abort, populate, or list in _SKIPPED.md)"
                )
            continue
        r_errors, r_warnings = validate_round_state(
            plan_path, rounds_dir=args.rounds_dir
        )
        errors.extend(r_errors)
        warnings.extend(r_warnings)

    # R50 opt K: soft check that provenance paths exist on disk.
    # Gitignored areas (results/, logs/) routinely produce warnings;
    # users skim past them. Never blocks validation.
    repo_root = Path(__file__).resolve().parents[2]
    warnings.extend(check_provenance_paths(claims, repo_root=repo_root))

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
