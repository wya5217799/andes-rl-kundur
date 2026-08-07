"""Build one bounded cold-start context for a research session.

Motivation
----------
The durable ledger may grow without bound, but a new agent session should not
load that history.  This tool combines the programme selector with the active
manuscript registry and returns only the current objective, gates, and files
that must be read now.

Usage
-----
    python memory/tools/session_context.py
    python memory/tools/session_context.py --json
    python memory/tools/session_context.py --json --list-lines
    python memory/tools/session_context.py --json --line sci-upgrade-survey
    python memory/tools/session_context.py --root C:\\path\\to\\checkout

Failure modes
-------------
Malformed programme state, manuscript-line metadata, missing required files,
ambiguous manuscript priorities, or a reading set above the fixed file/byte
budgets exit 4.  The tool is read-only and never reserves work or writes a
context file.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml  # type: ignore[import-untyped]
from research_goal import ProgrammeError, select_next_goal

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from andes_rl_kundur.repo_governance import (  # noqa: E402
    ContractError,
    inspect_manuscript_lines,
)
from andes_rl_kundur.round_scope import (  # noqa: E402
    RoundScopeError,
    resolve_line_selector,
)

CONTRACT_PATH = Path("docs/repo-hygiene/contract.json")
ROUND_SKILL = "skills/kundur-round/SKILL.md"
ROUND_RESUME_CONTRACT = "skills/kundur-round/references/resume-contract.md"
ENGINEERING_RULES = "CLAUDE.md"
MAX_REQUIRED_READING = 8
DEFAULT_MAX_REQUIRED_READING_BYTES = 24576
_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class ContextError(ValueError):
    """The repository cannot produce an unambiguous bounded session context."""


@dataclasses.dataclass(frozen=True)
class SessionContext:
    mode: str
    objective: str
    stage: str
    authority: str
    required_reading: tuple[str, ...]
    verification: tuple[str, ...]
    stop_when: tuple[str, ...]
    read_scope: tuple[str, ...] = ()
    write_scope: tuple[str, ...] = ()
    artifact_manifest: str | None = None
    venue_status: str | None = None
    primary_venue: str | None = None
    question_id: str | None = None
    active_rounds: tuple[str, ...] = ()
    manuscript_line: str | None = None
    artifact_alerts: tuple[str, ...] = ()
    decision_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        value = dataclasses.asdict(self)
        value["reading_file_count"] = len(self.required_reading)
        value["history_lookup"] = (
            "python memory/tools/note_query.py --topic <topic> --grep <keyword>"
        )
        return value


@dataclasses.dataclass(frozen=True)
class ManuscriptContext:
    line_id: str
    line_root: str
    priority: int
    stage: str
    objective: str
    required_reading: tuple[str, ...]
    verification: tuple[str, ...]
    stop_when: tuple[str, ...]
    read_scope: tuple[str, ...]
    write_scope: tuple[str, ...]
    artifact_manifest: str
    venue_status: str
    primary_venue: str | None
    artifact_alerts: tuple[str, ...]
    decision_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class ManuscriptLineRecord:
    """One discoverable manuscript delivery line and its routing readiness."""

    line_id: str
    status: str
    line_root: str
    has_line: bool
    has_manifest: bool
    selectable: bool
    routing_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContextError(f"missing repository contract: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ContextError(f"cannot read repository contract {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContextError(f"{path}: root must be an object")
    return value


def list_manuscript_lines(repo_root: Path = ROOT) -> tuple[ManuscriptLineRecord, ...]:
    """List manuscript lines without loading programme or evidence history."""

    repo_root = repo_root.resolve()
    contract_path = repo_root / CONTRACT_PATH
    contract = _load_json(contract_path)
    lines = contract.get("delivery_lines", [])
    if not isinstance(lines, list):
        raise ContextError(f"{contract_path}: delivery_lines must be a list")

    records: list[ManuscriptLineRecord] = []
    seen: set[str] = set()
    for line in lines:
        if not isinstance(line, dict):
            raise ContextError(f"{contract_path}: delivery line must be an object")
        if line.get("kind") != "manuscript":
            continue
        line_id = line.get("id")
        status = line.get("status")
        root_value = line.get("root")
        if (
            not isinstance(line_id, str)
            or not line_id.strip()
            or not isinstance(status, str)
            or not status.strip()
            or not isinstance(root_value, str)
            or not root_value.strip()
        ):
            raise ContextError(f"{contract_path}: manuscript id/status/root invalid")
        if line_id in seen:
            raise ContextError(f"{contract_path}: duplicate manuscript line id {line_id}")
        seen.add(line_id)
        line_root = _relative(
            root_value,
            field="delivery_lines.root",
            source=contract_path,
        )
        line_entry = repo_root / line_root / "LINE.md"
        manifest = repo_root / line_root / "ARTIFACTS.json"
        has_line = line_entry.is_file()
        has_manifest = manifest.is_file()
        selectable = False
        routing_error: str | None = None
        if status == "active":
            if not has_line or not has_manifest:
                missing = []
                if not has_line:
                    missing.append("LINE.md")
                if not has_manifest:
                    missing.append("ARTIFACTS.json")
                routing_error = f"missing routing metadata: {', '.join(missing)}"
            else:
                try:
                    selectable = bool(
                        _active_manuscripts(repo_root, only_line=line_id)
                    )
                except ContextError as exc:
                    routing_error = str(exc)
        records.append(
            ManuscriptLineRecord(
                line_id=line_id,
                status=status,
                line_root=line_root.as_posix(),
                has_line=has_line,
                has_manifest=has_manifest,
                selectable=selectable,
                routing_error=routing_error,
            )
        )
    return tuple(records)


def _frontmatter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ContextError(f"missing manuscript entry: {path}") from exc
    except OSError as exc:
        raise ContextError(f"cannot read manuscript entry {path}: {exc}") from exc
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ContextError(f"{path}: missing YAML frontmatter")
    try:
        value = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ContextError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(value, dict):
        raise ContextError(f"{path}: frontmatter must be a mapping")
    return value


def _required_string(meta: dict[str, Any], key: str, source: Path) -> str:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContextError(f"{source}: '{key}' must be a non-empty string")
    return value.strip()


def _string_list(meta: dict[str, Any], key: str, source: Path) -> tuple[str, ...]:
    value = meta.get(key)
    if not isinstance(value, list) or not value:
        raise ContextError(f"{source}: '{key}' must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContextError(f"{source}: '{key}' entries must be non-empty strings")
    return tuple(item.strip() for item in value)


def _optional_string_list(
    meta: dict[str, Any],
    key: str,
    source: Path,
) -> tuple[str, ...]:
    value = meta.get(key, [])
    if not isinstance(value, list):
        raise ContextError(f"{source}: '{key}' must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContextError(f"{source}: '{key}' entries must be non-empty strings")
    return tuple(item.strip() for item in value)


def _navigation_refs(
    repo_root: Path,
    meta: dict[str, Any],
    key: str,
    source: Path,
) -> tuple[str, ...]:
    refs = _optional_string_list(meta, key, source)
    for value in refs:
        if key == "decision_refs":
            path_text, separator, locator = value.partition("#")
            if not separator or not locator.strip():
                raise ContextError(f"{source}: decision_refs entries must use path#locator")
            target = path_text.strip()
        else:
            match = re.fullmatch(r"(CLM-\d+)\s*->\s*(.+)", value)
            if match is None:
                raise ContextError(f"{source}: evidence_refs entries must use CLM-NNNN -> path")
            claim_path = repo_root / "memory" / "claims" / f"{match.group(1)}.md"
            if not claim_path.is_file():
                raise ContextError(f"{source}: evidence_refs claim is missing: {match.group(1)}")
            target = match.group(2).strip()
        relative = _relative(target, field=key, source=source)
        if not (repo_root / relative).is_file():
            raise ContextError(f"{source}: {key} target is missing: {target}")
    return refs


def _relative(value: str, *, field: str, source: Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ContextError(f"{source}: '{field}' must stay inside the repository")
    return path


def _within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _bounded_reading(repo_root: Path, values: tuple[str, ...]) -> tuple[str, ...]:
    unique = tuple(dict.fromkeys(values))
    if len(unique) > MAX_REQUIRED_READING:
        raise ContextError(
            f"required_reading has {len(unique)} files; budget is "
            f"{MAX_REQUIRED_READING}. Consolidate the entry pointers."
        )
    missing = [value for value in unique if not (repo_root / value).is_file()]
    if missing:
        raise ContextError(f"required_reading files are missing: {missing}")
    contract = _load_json(repo_root / CONTRACT_PATH)
    manuscript_policy = contract.get("manuscript_lines", {})
    if not isinstance(manuscript_policy, dict):
        raise ContextError("manuscript_lines must be an object")
    budgets = manuscript_policy.get("navigation_budgets", {})
    if not isinstance(budgets, dict):
        raise ContextError("manuscript_lines.navigation_budgets must be an object")
    byte_budget = budgets.get(
        "required_reading_max_bytes",
        DEFAULT_MAX_REQUIRED_READING_BYTES,
    )
    if isinstance(byte_budget, bool) or not isinstance(byte_budget, int) or byte_budget < 1:
        raise ContextError(
            "manuscript_lines.navigation_budgets."
            "required_reading_max_bytes must be a positive integer"
        )
    byte_count = sum((repo_root / value).stat().st_size for value in unique)
    if byte_count > byte_budget:
        raise ContextError(
            f"required_reading is {byte_count} bytes; budget is {byte_budget}. "
            "Replace copied facts with lazy decision/evidence pointers."
        )
    return unique


def _manuscript_scope(
    repo_root: Path,
    entry: Path,
    line_root: Path,
    meta: dict[str, Any],
    required_reading: tuple[str, ...],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    scope = meta.get("scope")
    if not isinstance(scope, dict):
        raise ContextError(f"{entry}: 'scope' must be a mapping")
    write_values = _string_list(scope, "write_roots", entry)
    read_values = _optional_string_list(scope, "shared_read_roots", entry)
    write_paths = tuple(
        _relative(value, field="scope.write_roots", source=entry) for value in write_values
    )
    read_paths = tuple(
        _relative(value, field="scope.shared_read_roots", source=entry) for value in read_values
    )
    if line_root not in write_paths:
        raise ContextError(
            f"{entry}: scope.write_roots must include delivery root {line_root.as_posix()}"
        )
    outside = [path.as_posix() for path in write_paths if not _within(path, line_root)]
    if outside:
        raise ContextError(f"{entry}: manuscript write scope escapes its delivery root: {outside}")
    missing_roots = [
        path.as_posix() for path in (*write_paths, *read_paths) if not (repo_root / path).exists()
    ]
    if missing_roots:
        raise ContextError(f"{entry}: declared scope roots are missing: {missing_roots}")
    allowed = (*write_paths, *read_paths)
    outside_reading = [
        value
        for value in required_reading
        if not any(
            _within(
                _relative(value, field="required_reading", source=entry),
                allowed_root,
            )
            for allowed_root in allowed
        )
    ]
    if outside_reading:
        raise ContextError(f"{entry}: required_reading escapes declared scope: {outside_reading}")
    return (
        tuple(path.as_posix() for path in dict.fromkeys((*write_paths, *read_paths))),
        tuple(path.as_posix() for path in write_paths),
    )


def _venue(
    repo_root: Path,
    entry: Path,
    meta: dict[str, Any],
) -> tuple[str, str | None]:
    venue = meta.get("venue")
    if not isinstance(venue, dict):
        raise ContextError(f"{entry}: 'venue' must be a mapping")
    status = _required_string(venue, "status", entry)
    valid_statuses = {"unassessed", "shortlisted", "locked", "revalidate"}
    if status not in valid_statuses:
        raise ContextError(f"{entry}: venue.status must be one of {sorted(valid_statuses)}")
    kind = venue.get("kind", "journal")
    if kind not in {"journal", "conference", "other"}:
        raise ContextError(f"{entry}: venue.kind must be journal, conference, or other")
    official_status = _required_string(venue, "official_source_status", entry)
    if official_status not in {"unverified", "partial", "current"}:
        raise ContextError(
            f"{entry}: venue.official_source_status must be unverified, partial, or current"
        )
    primary = venue.get("primary")
    if primary is not None and (not isinstance(primary, str) or not primary.strip()):
        raise ContextError(f"{entry}: venue.primary must be a non-empty string")
    if status != "unassessed":
        if not isinstance(primary, str) or not primary.strip():
            raise ContextError(f"{entry}: selected venue state requires venue.primary")
        backup = venue.get("backup")
        if kind == "journal" and (not isinstance(backup, str) or not backup.strip()):
            raise ContextError(f"{entry}: selected journal state requires venue.backup")
        if backup is not None and (not isinstance(backup, str) or not backup.strip()):
            raise ContextError(f"{entry}: venue.backup must be a non-empty string")
        record = _required_string(venue, "decision_record", entry)
        record_path = _relative(record, field="venue.decision_record", source=entry)
        if not (repo_root / record_path).is_file():
            raise ContextError(f"{entry}: venue decision record is missing: {record}")
    if status == "locked" and official_status != "current":
        raise ContextError(f"{entry}: a locked venue requires current official-source verification")
    return status, primary.strip() if isinstance(primary, str) else None


def _active_manuscripts(
    repo_root: Path,
    *,
    only_line: str | None = None,
) -> tuple[ManuscriptContext, ...]:
    contract_path = repo_root / CONTRACT_PATH
    contract = _load_json(contract_path)
    lines = contract.get("delivery_lines", [])
    if not isinstance(lines, list):
        raise ContextError(f"{contract_path}: delivery_lines must be a list")

    active: list[ManuscriptContext] = []
    try:
        governance_findings = inspect_manuscript_lines(repo_root)
    except ContractError as exc:
        raise ContextError(str(exc)) from exc
    for line in lines:
        if not isinstance(line, dict):
            raise ContextError(f"{contract_path}: delivery line must be an object")
        if line.get("kind") != "manuscript" or line.get("status") != "active":
            continue
        if only_line is not None and line.get("id") != only_line:
            continue
        line_id = line.get("id")
        root_value = line.get("root")
        if not isinstance(line_id, str) or not isinstance(root_value, str):
            raise ContextError(f"{contract_path}: active manuscript id/root invalid")
        entry = repo_root / root_value / "LINE.md"
        meta = _frontmatter(entry)
        if _required_string(meta, "line_id", entry) != line_id:
            raise ContextError(f"{entry}: line_id does not match contract id {line_id}")
        if _required_string(meta, "status", entry) != "active":
            raise ContextError(f"{entry}: active contract line must have status active")
        priority = meta.get("priority")
        if not isinstance(priority, int) or priority < 1:
            raise ContextError(f"{entry}: priority must be a positive integer")
        manifest = _required_string(meta, "artifact_manifest", entry)
        manifest_path = _relative(
            manifest,
            field="artifact_manifest",
            source=entry,
        )
        if not (repo_root / manifest_path).is_file():
            raise ContextError(f"{entry}: artifact manifest is missing: {manifest}")
        required_reading = _bounded_reading(
            repo_root,
            (
                *_string_list(meta, "required_reading", entry),
                manifest_path.as_posix(),
            ),
        )
        read_scope, write_scope = _manuscript_scope(
            repo_root,
            entry,
            Path(root_value),
            meta,
            required_reading,
        )
        venue_status, primary_venue = _venue(repo_root, entry, meta)
        decision_refs = _navigation_refs(
            repo_root,
            meta,
            "decision_refs",
            entry,
        )
        evidence_refs = _navigation_refs(
            repo_root,
            meta,
            "evidence_refs",
            entry,
        )
        line_prefix = f"{Path(root_value).as_posix()}/"
        artifact_alerts = tuple(
            f"{finding.rule_id}: {finding.path}: {finding.message}"
            for finding in governance_findings
            if (
                finding.severity == "error"
                and (
                    finding.rule_id.startswith("DOCUMENT_")
                    or finding.rule_id.startswith("MANUSCRIPT_")
                    or finding.rule_id == "VENUE_DECISION_MISSING"
                )
                and (
                    finding.path == Path(root_value).as_posix()
                    or finding.path.startswith(line_prefix)
                )
            )
        )
        if any(
            alert.startswith(("DOCUMENT_REVIEW_EXPIRED:", "DOCUMENT_INPUT_DRIFT:"))
            for alert in artifact_alerts
        ):
            venue_status = "revalidate"
        active.append(
            ManuscriptContext(
                line_id=line_id,
                line_root=root_value,
                priority=priority,
                stage=_required_string(meta, "stage", entry),
                objective=_required_string(meta, "objective", entry),
                required_reading=required_reading,
                verification=_string_list(meta, "verification", entry),
                stop_when=_string_list(meta, "stop_when", entry),
                read_scope=read_scope,
                write_scope=write_scope,
                artifact_manifest=manifest_path.as_posix(),
                venue_status=venue_status,
                primary_venue=primary_venue,
                artifact_alerts=artifact_alerts,
                decision_refs=decision_refs,
                evidence_refs=evidence_refs,
            )
        )

    active.sort(key=lambda item: (item.priority, item.line_id))
    if len(active) > 1 and active[0].priority == active[1].priority:
        raise ContextError(
            "multiple active manuscript lines share top priority "
            f"{active[0].priority}: {active[0].line_id}, {active[1].line_id}"
        )
    return tuple(active)


def _select_manuscript(
    manuscripts: tuple[ManuscriptContext, ...],
    manuscript_line: str | None,
) -> ManuscriptContext | None:
    if not manuscripts:
        return None
    if manuscript_line is None:
        return manuscripts[0]
    line = next(
        (item for item in manuscripts if item.line_id == manuscript_line),
        None,
    )
    if line is None:
        choices = ", ".join(item.line_id for item in manuscripts)
        raise ContextError(
            f"requested manuscript line is not active: {manuscript_line}; "
            f"active choices: {choices or '(none)'}"
        )
    return line


def _manuscript_session(line: ManuscriptContext) -> SessionContext:
    freshness_alerts = tuple(
        alert
        for alert in line.artifact_alerts
        if alert.startswith(
            (
                "DOCUMENT_REVIEW_EXPIRED:",
                "DOCUMENT_INPUT_DRIFT:",
                "DOCUMENT_NAVIGATION_",
                "MANUSCRIPT_",
            )
        )
    )
    if freshness_alerts:
        return SessionContext(
            mode="manuscript-refresh",
            objective=(
                f"Refresh or supersede stale manuscript artifacts before continuing {line.line_id}."
            ),
            stage="artifact-refresh",
            authority="ARTIFACTS.json freshness contract + current source inputs",
            required_reading=line.required_reading,
            verification=(
                "Refresh or supersede every expired or input-drifted active artifact.",
                "Run python scripts/repo_health.py check --no-baseline.",
            ),
            stop_when=("The active manuscript line has no artifact freshness alerts.",),
            read_scope=line.read_scope,
            write_scope=line.write_scope,
            artifact_manifest=line.artifact_manifest,
            venue_status="revalidate",
            primary_venue=line.primary_venue,
            manuscript_line=line.line_id,
            artifact_alerts=line.artifact_alerts,
            decision_refs=line.decision_refs,
            evidence_refs=line.evidence_refs,
        )
    return SessionContext(
        mode="manuscript",
        objective=line.objective,
        stage=line.stage,
        authority="LINE.md decisions + CLM/feed/results evidence hierarchy",
        required_reading=line.required_reading,
        verification=line.verification,
        stop_when=line.stop_when,
        read_scope=line.read_scope,
        write_scope=line.write_scope,
        artifact_manifest=line.artifact_manifest,
        venue_status=line.venue_status,
        primary_venue=line.primary_venue,
        manuscript_line=line.line_id,
        artifact_alerts=line.artifact_alerts,
        decision_refs=line.decision_refs,
        evidence_refs=line.evidence_refs,
    )


def build_session_context(
    repo_root: Path = ROOT,
    manuscript_line: str | None = None,
) -> SessionContext:
    repo_root = repo_root.resolve()
    if manuscript_line is not None:
        try:
            manuscript_line = resolve_line_selector(
                repo_root,
                manuscript_line,
                require_active=True,
            )
        except RoundScopeError as exc:
            raise ContextError(str(exc)) from exc
    try:
        goal = select_next_goal(repo_root, manuscript_line=manuscript_line)
    except ProgrammeError as exc:
        raise ContextError(str(exc)) from exc

    if goal.status == "blocked-active-round":
        # Resume is execution-only under the frozen plan and compact resume
        # contract.  AGENTS.md separately requires CLAUDE.md before any code or
        # governance change, so loading the full engineering manual here would
        # duplicate policy and can crowd a legitimate active plan out of the
        # bounded cold-start budget.
        reading = _bounded_reading(
            repo_root,
            (
                ROUND_RESUME_CONTRACT,
                *(f"memory/rounds/{round_id}/plan.md" for round_id in goal.active_rounds),
            ),
        )
        return SessionContext(
            mode="resume-round",
            objective="Resume and close the active round before starting new work.",
            stage=goal.phase,
            authority="active round plan + research programme + sealed evidence",
            required_reading=reading,
            verification=("follow the active plan's frozen verification contract",),
            stop_when=("the active round satisfies the kundur-round close-out contract",),
            active_rounds=goal.active_rounds,
            manuscript_line=manuscript_line,
        )

    manuscripts: tuple[ManuscriptContext, ...] | None = None
    if manuscript_line is not None:
        manuscripts = _active_manuscripts(repo_root, only_line=manuscript_line)
        line = _select_manuscript(manuscripts, manuscript_line)
        if line is None:
            raise ContextError(
                f"requested manuscript line is not active: {manuscript_line}; "
                "active choices: (none)"
            )
        return _manuscript_session(line)

    if goal.status == "ready":
        reading = _bounded_reading(
            repo_root,
            (ENGINEERING_RULES, ROUND_SKILL, *goal.required_reading),
        )
        return SessionContext(
            mode="research",
            objective=goal.objective or "",
            stage=goal.phase,
            authority="research programme + selected question + sealed evidence",
            required_reading=reading,
            verification=goal.verification,
            stop_when=goal.stop_when,
            question_id=goal.question_id,
        )

    manuscripts = _active_manuscripts(repo_root)
    line = _select_manuscript(manuscripts, None)
    if line is not None:
        return _manuscript_session(line)

    reading = _bounded_reading(repo_root, ("memory/RESEARCH_PROGRAM.md",))
    return SessionContext(
        mode="idle",
        objective="No authorized research question or active manuscript action.",
        stage=goal.phase,
        authority="research programme",
        required_reading=reading,
        verification=("do not reserve a round without a prospectively authorized question",),
        stop_when=("the user authorizes a bounded next action or the programme is updated",),
    )


def _render(context: SessionContext) -> str:
    def bullets(values: tuple[str, ...]) -> str:
        return "\n".join(f"- {value}" for value in values)

    return (
        f"MODE: {context.mode}\n"
        f"OBJECTIVE: {context.objective}\n"
        f"STAGE: {context.stage}\n"
        f"AUTHORITY: {context.authority}\n"
        f"READ SCOPE: {', '.join(context.read_scope) or '-'}\n"
        f"WRITE SCOPE: {', '.join(context.write_scope) or '-'}\n"
        f"VENUE: {context.venue_status or '-'} / "
        f"{context.primary_venue or '-'}\n"
        f"ARTIFACT ALERTS: {len(context.artifact_alerts)}\n"
        f"{bullets(context.artifact_alerts) if context.artifact_alerts else '-'}\n"
        "DECISION REFS:\n"
        f"{bullets(context.decision_refs) if context.decision_refs else '-'}\n"
        "EVIDENCE REFS:\n"
        f"{bullets(context.evidence_refs) if context.evidence_refs else '-'}\n"
        f"READ ({len(context.required_reading)}/{MAX_REQUIRED_READING} files):\n"
        f"{bullets(context.required_reading)}\n"
        "VERIFY:\n"
        f"{bullets(context.verification)}\n"
        "STOP WHEN:\n"
        f"{bullets(context.stop_when)}"
    )


def _render_line_catalog(lines: tuple[ManuscriptLineRecord, ...]) -> str:
    if not lines:
        return "MANUSCRIPT LINES: none"
    rendered = ["MANUSCRIPT LINES:"]
    for line in lines:
        readiness = "selectable" if line.selectable else "not-selectable"
        error = f", reason={line.routing_error}" if line.routing_error else ""
        rendered.append(f"- {line.line_id}: {line.status}, {readiness}, root={line.line_root}{error}")
    return "\n".join(rendered)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument(
        "--line",
        help="Select one active manuscript line instead of the top-priority line.",
    )
    selection.add_argument(
        "--list-lines",
        action="store_true",
        help="List manuscript lines and whether each is selectable.",
    )
    args = parser.parse_args(argv)
    try:
        if args.list_lines:
            lines = list_manuscript_lines(args.root)
        else:
            context = build_session_context(args.root, manuscript_line=args.line)
    except ContextError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4
    if args.list_lines:
        if args.json:
            print(
                json.dumps(
                    {"manuscript_lines": [line.as_dict() for line in lines]},
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(_render_line_catalog(lines))
        return 0
    if args.json:
        print(json.dumps(context.as_dict(), ensure_ascii=False, indent=2))
    else:
        print(_render(context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
