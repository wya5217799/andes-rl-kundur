"""Select the next TPWRS-oriented research goal from repository state.

Motivation
----------
``memory/STATE.md`` answers "what is true now?" and the question ledger
answers "what remains open?", but neither records which open question advances
the accepted paper thesis.  Chat memory is not a reliable policy store.  This
module combines the durable programme, question states, and active-round
preflight behind one small interface.

Interface
---------
Library:

    selection = select_next_goal(repo_root)
    selection.status       # "ready", "blocked-active-round", "no-eligible-question"
    selection.prompt       # complete /goal prompt when status == "ready"

CLI:

    python memory/tools/research_goal.py
    python memory/tools/research_goal.py --json

The selector is deliberately read-only.  It never reserves a round, launches
ANDES, edits a question, or creates a Codex goal.  Callers decide when to act
on the returned contract.

Failure modes
-------------
Malformed programme/question frontmatter and missing required-reading files
fail loudly with ``ProgrammeError`` (CLI exit 4).  A genuinely active round is
not an error: it returns ``blocked-active-round`` (CLI exit 2) so autonomous
sessions resume existing work instead of duplicating it.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from reserve_round import _active_rounds_in_progress
from reserve_round import _active_rounds_in_scope

ROOT = Path(__file__).resolve().parents[2]
PROGRAMME_PATH = Path("memory/RESEARCH_PROGRAM.md")
OPEN_QUESTION_STATES = {"open", "in-flight"}
_FRONTMATTER_RE = re.compile(r"^---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


class ProgrammeError(ValueError):
    """The durable programme cannot produce a trustworthy goal."""


@dataclasses.dataclass(frozen=True)
class GoalSelection:
    """Observable result of :func:`select_next_goal`."""

    status: str
    programme_id: str
    phase: str
    question_id: str | None = None
    objective: str | None = None
    required_reading: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()
    scope_limits: tuple[str, ...] = ()
    stop_when: tuple[str, ...] = ()
    active_rounds: tuple[str, ...] = ()
    prompt: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return a stable JSON-serialisable representation."""
        return dataclasses.asdict(self)


def _frontmatter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ProgrammeError(f"missing required file: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ProgrammeError(f"cannot read {path}: {exc}") from exc
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise ProgrammeError(f"{path}: missing YAML frontmatter")
    try:
        value = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise ProgrammeError(f"{path}: invalid YAML frontmatter: {exc}") from exc
    if not isinstance(value, dict):
        raise ProgrammeError(f"{path}: frontmatter must be a mapping")
    return value


def _required_string(meta: dict[str, Any], key: str, source: Path) -> str:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProgrammeError(f"{source}: '{key}' must be a non-empty string")
    return value.strip()


def _string_list(value: Any, *, key: str, source: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ProgrammeError(f"{source}: '{key}' must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ProgrammeError(f"{source}: '{key}' entries must be non-empty strings")
    return tuple(item.strip() for item in value)


def _active_rounds(
    repo_root: Path,
    manuscript_line: str | None = None,
) -> tuple[str, ...]:
    """Return rounds whose lifecycle frontmatter still requires closure."""
    rounds_dir = repo_root / "memory" / "rounds"
    active = _active_rounds_in_progress(rounds_dir)
    active = _active_rounds_in_scope(
        active,
        repo_root=repo_root,
        rounds_dir=rounds_dir,
        manuscript_line=manuscript_line,
    )
    return tuple(name for _, _, name in active)


def _question_index(repo_root: Path) -> dict[str, tuple[dict[str, Any], Path]]:
    questions_dir = repo_root / "memory" / "questions"
    result: dict[str, tuple[dict[str, Any], Path]] = {}
    if not questions_dir.is_dir():
        return result
    for path in sorted(questions_dir.glob("Q-*.md")):
        meta = _frontmatter(path)
        qid = _required_string(meta, "id", path)
        if qid in result:
            raise ProgrammeError(f"duplicate question id: {qid}")
        result[qid] = (meta, path)
    return result


def _render_prompt(
    *,
    objective: str,
    required_reading: tuple[str, ...],
    verification: tuple[str, ...],
    scope_limits: tuple[str, ...],
    stop_when: tuple[str, ...],
) -> str:
    def bullets(items: tuple[str, ...]) -> str:
        return "\n".join(f"- {item}" for item in items)

    return (
        f"/goal Complete this research objective: {objective}\n\n"
        "Read these authoritative sources first:\n"
        f"{bullets(required_reading)}\n\n"
        "Stay within these scope limits:\n"
        f"{bullets(scope_limits)}\n\n"
        "Use these verification commands or evidence checks:\n"
        f"{bullets(verification)}\n\n"
        "Stop only when all of these conditions are proven:\n"
        f"{bullets(stop_when)}"
    )


def select_next_goal(
    repo_root: Path = ROOT,
    manuscript_line: str | None = None,
) -> GoalSelection:
    """Return the next programme-ranked goal without changing repository state.

    Selection order:
    1. Refuse new work when a genuinely active round exists.
    2. Sort ``priority_questions`` by ascending integer ``rank``.
    3. Choose the first listed question whose ledger state is open/in-flight.
    4. Return ``no-eligible-question`` when all programme questions are
       closed or none are listed (an empty list is a clean no-goal state,
       not a malformed programme).
    """
    repo_root = repo_root.resolve()
    programme_path = repo_root / PROGRAMME_PATH
    programme = _frontmatter(programme_path)

    if programme.get("status") != "active":
        raise ProgrammeError(f"{programme_path}: programme status must be 'active'")
    programme_id = _required_string(programme, "programme_id", programme_path)
    phase = _required_string(programme, "current_phase", programme_path)

    active = _active_rounds(repo_root, manuscript_line=manuscript_line)
    if active:
        return GoalSelection(
            status="blocked-active-round",
            programme_id=programme_id,
            phase=phase,
            active_rounds=active,
        )

    priorities = programme.get("priority_questions") or []
    if not isinstance(priorities, list):
        raise ProgrammeError(f"{programme_path}: 'priority_questions' must be a list when present")
    questions = _question_index(repo_root)

    ranked: list[tuple[int, int, dict[str, Any]]] = []
    for order, item in enumerate(priorities):
        if not isinstance(item, dict):
            raise ProgrammeError(
                f"{programme_path}: every priority_questions item must be a mapping"
            )
        qid = _required_string(item, "id", programme_path)
        rank = item.get("rank")
        if not isinstance(rank, int):
            raise ProgrammeError(f"{programme_path}: rank for {qid} must be an integer")
        ranked.append((rank, order, item))

    for _, _, item in sorted(ranked):
        qid = str(item["id"]).strip()
        if qid not in questions:
            raise ProgrammeError(f"{programme_path}: priority question {qid} has no ledger file")
        question, question_path = questions[qid]
        state = _required_string(question, "status", question_path)
        if state not in OPEN_QUESTION_STATES:
            continue

        item_phase = _required_string(item, "phase", programme_path)
        if item_phase != phase:
            continue
        objective = _required_string(item, "objective", programme_path)
        reading = _string_list(
            item.get("required_reading"),
            key=f"{qid}.required_reading",
            source=programme_path,
        )
        verification = _string_list(
            item.get("verification"),
            key=f"{qid}.verification",
            source=programme_path,
        )
        limits = _string_list(
            item.get("scope_limits"),
            key=f"{qid}.scope_limits",
            source=programme_path,
        )
        stop_when = _string_list(
            item.get("stop_when"),
            key=f"{qid}.stop_when",
            source=programme_path,
        )

        missing = [path for path in reading if not (repo_root / path).is_file()]
        if missing:
            raise ProgrammeError(f"{programme_path}: {qid} required_reading missing: {missing}")

        return GoalSelection(
            status="ready",
            programme_id=programme_id,
            phase=phase,
            question_id=qid,
            objective=objective,
            required_reading=reading,
            verification=verification,
            scope_limits=limits,
            stop_when=stop_when,
            prompt=_render_prompt(
                objective=objective,
                required_reading=reading,
                verification=verification,
                scope_limits=limits,
                stop_when=stop_when,
            ),
        )

    return GoalSelection(
        status="no-eligible-question",
        programme_id=programme_id,
        phase=phase,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Select the next TPWRS-oriented repository research goal."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repository root (defaults to this tool's repository)",
    )
    parser.add_argument(
        "--line",
        help="Limit active-round blocking to one manuscript line.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the full selection as JSON",
    )
    args = parser.parse_args(argv)

    try:
        selection = select_next_goal(args.root, manuscript_line=args.line)
    except ProgrammeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    if args.json:
        print(json.dumps(selection.as_dict(), ensure_ascii=False, indent=2))
    elif selection.status == "ready":
        print(selection.prompt)
    elif selection.status == "blocked-active-round":
        print(
            "BLOCKED: resume active round(s): " + ", ".join(selection.active_rounds),
            file=sys.stderr,
        )
    else:
        print(
            "NO GOAL: no programme-ranked open question in the current phase.",
            file=sys.stderr,
        )

    return {
        "ready": 0,
        "blocked-active-round": 2,
        "no-eligible-question": 3,
    }[selection.status]


if __name__ == "__main__":
    raise SystemExit(main())
