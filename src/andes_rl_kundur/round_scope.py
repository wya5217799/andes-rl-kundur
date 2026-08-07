"""Resolve manuscript-line ownership for research rounds.

This module is the single seam between repository manuscript metadata and
round lifecycle tools.  New rounds declare ``manuscript_line`` in plan
frontmatter.  Frozen legacy plans may instead be resolved from their existing
``Selected line: `paper/...``` sentence; no historical plan is rewritten.

An unresolved round is deliberately treated as repository-global by callers.
That conservative fallback prevents old or malformed work from being ignored
when a manuscript-scoped session starts.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Mapping


CONTRACT_PATH = Path("docs/repo-hygiene/contract.json")
_NULL_VALUES = {"", "null", "none", "~"}
_SELECTED_LINE_RE = re.compile(
    r"(?mi)^\s*[-*]?\s*(?:\*\*)?Selected line(?:\*\*)?\s*:\s*"
    r"`(?P<root>[^`]+)`"
)


class RoundScopeError(ValueError):
    """Round ownership cannot be resolved against the repository contract."""


@dataclasses.dataclass(frozen=True)
class ManuscriptLine:
    line_id: str
    root: str
    status: str


def manuscript_lines(repo_root: Path) -> tuple[ManuscriptLine, ...]:
    """Return manuscript delivery lines declared by the repository contract."""

    contract_path = repo_root.resolve() / CONTRACT_PATH
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RoundScopeError(f"missing repository contract: {contract_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RoundScopeError(f"cannot read repository contract {contract_path}: {exc}") from exc
    values = contract.get("delivery_lines", [])
    if not isinstance(values, list):
        raise RoundScopeError(f"{contract_path}: delivery_lines must be a list")

    result: list[ManuscriptLine] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict) or value.get("kind") != "manuscript":
            continue
        line_id = value.get("id")
        root = value.get("root")
        status = value.get("status")
        if not all(isinstance(item, str) and item.strip() for item in (line_id, root, status)):
            raise RoundScopeError(
                f"{contract_path}: manuscript delivery_lines[{index}] has invalid id/root/status"
            )
        result.append(
            ManuscriptLine(
                line_id=line_id.strip(),
                root=Path(root.strip()).as_posix(),
                status=status.strip(),
            )
        )
    return tuple(result)


def resolve_line_selector(
    repo_root: Path,
    selector: str,
    *,
    require_active: bool = False,
) -> str:
    """Resolve a line id, delivery root, or unique root basename to its id."""

    raw = selector.strip().replace("\\", "/").rstrip("/")
    lines = manuscript_lines(repo_root)
    candidates = [
        line
        for line in lines
        if raw == line.line_id
        or raw == line.root
        or raw == Path(line.root).name
    ]
    if require_active:
        candidates = [line for line in candidates if line.status == "active"]
    if len(candidates) == 1:
        return candidates[0].line_id
    choices = ", ".join(
        line.line_id for line in lines if not require_active or line.status == "active"
    )
    if not candidates:
        qualifier = "active " if require_active else ""
        raise RoundScopeError(
            f"unknown {qualifier}manuscript line {selector!r}; choices: {choices or '(none)'}"
        )
    raise RoundScopeError(f"ambiguous manuscript line selector {selector!r}")


def resolve_round_line(
    repo_root: Path,
    plan_path: Path,
    frontmatter: Mapping[str, object],
) -> str | None:
    """Return a round's manuscript line, or ``None`` for a global lock.

    Explicit frontmatter is authoritative.  The legacy body fallback is used
    only when the field is absent, preserving frozen plans byte-for-byte.
    """

    if "manuscript_line" in frontmatter:
        value = frontmatter.get("manuscript_line")
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if cleaned.lower() in _NULL_VALUES:
            return None
        try:
            return resolve_line_selector(repo_root, cleaned)
        except RoundScopeError:
            # Keep an explicit unknown id distinguishable from an unowned
            # round. Validators can report it; conflict checks remain safe.
            return cleaned

    try:
        body = plan_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _SELECTED_LINE_RE.search(body)
    if match is None:
        return None
    try:
        return resolve_line_selector(repo_root, match.group("root"))
    except RoundScopeError:
        return None


def lines_conflict(round_line: str | None, requested_line: str | None) -> bool:
    """Return whether an active round blocks a requested ownership scope."""

    if requested_line is None:
        return True
    return round_line is None or round_line == requested_line
