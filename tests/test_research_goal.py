"""Behavioural tests for the TPWRS research-goal selector.

The public interface is ``select_next_goal(repo_root)``.  Tests deliberately
avoid asserting internal helper behaviour so programme parsing and round-state
implementation can change without rewriting the suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "memory" / "tools"
sys.path.insert(0, str(TOOLS))

from research_goal import ProgrammeError, select_next_goal  # noqa: E402


def _write_question(root: Path, qid: str, status: str) -> None:
    questions = root / "memory" / "questions"
    questions.mkdir(parents=True, exist_ok=True)
    (questions / f"{qid}.md").write_text(
        f"---\nid: {qid}\nstatus: {status}\ntitle: test {qid}\nopened_round: R1\n---\n",
        encoding="utf-8",
    )


def _write_required_files(root: Path) -> list[str]:
    paths = ["memory/STATE.md", "docs/audit.md"]
    for rel in paths:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("fixture\n", encoding="utf-8")
    return paths


def _write_programme(
    root: Path,
    priorities: list[tuple[str, int]],
    *,
    required_reading: list[str] | None = None,
) -> None:
    required_reading = required_reading or _write_required_files(root)
    items = []
    for qid, rank in priorities:
        items.append(
            "\n".join(
                [
                    f"  - id: {qid}",
                    f"    rank: {rank}",
                    "    phase: P0",
                    f"    objective: Test objective for {qid}.",
                    "    required_reading:",
                    *[f"      - {path}" for path in required_reading],
                    "    verification:",
                    "      - python verify.py",
                    "    scope_limits:",
                    "      - Do not change the environment.",
                    "    stop_when:",
                    f"      - {qid} has a recorded verdict.",
                ]
            )
        )
    programme = root / "memory" / "RESEARCH_PROGRAM.md"
    programme.parent.mkdir(parents=True, exist_ok=True)
    programme.write_text(
        "---\n"
        "version: 1\n"
        "status: active\n"
        "programme_id: test-programme\n"
        "current_phase: P0\n"
        "priority_questions:\n" + "\n".join(items) + "\n---\n# test programme\n",
        encoding="utf-8",
    )


def _write_round(
    root: Path,
    name: str,
    *,
    verdict: bool = False,
    manuscript_line: str | None = None,
) -> None:
    round_dir = root / "memory" / "rounds" / name
    round_dir.mkdir(parents=True, exist_ok=True)
    ownership = (
        f"manuscript_line: {manuscript_line}\n"
        if manuscript_line is not None
        else ""
    )
    (round_dir / "plan.md").write_text(
        f"---\nround: {name}\nstate: active\n{ownership}"
        "opened: '2026-07-24'\n---\n",
        encoding="utf-8",
    )
    if verdict:
        (round_dir / "verdict.md").write_text("# closed\n", encoding="utf-8")


def test_selects_highest_priority_open_question_and_renders_full_goal(
    tmp_path: Path,
) -> None:
    _write_programme(tmp_path, [("Q-0002", 20), ("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "open")
    _write_question(tmp_path, "Q-0002", "open")

    selected = select_next_goal(tmp_path)

    assert selected.status == "ready"
    assert selected.question_id == "Q-0001"
    assert selected.phase == "P0"
    assert selected.prompt.startswith("/goal Complete this research objective:")
    assert "Read these authoritative sources first:" in selected.prompt
    assert "Stay within these scope limits:" in selected.prompt
    assert "Use these verification commands" in selected.prompt
    assert "Stop only when all" in selected.prompt


def test_skips_closed_priority_question(tmp_path: Path) -> None:
    _write_programme(tmp_path, [("Q-0001", 10), ("Q-0002", 20)])
    _write_question(tmp_path, "Q-0001", "closed-negative")
    _write_question(tmp_path, "Q-0002", "open")

    selected = select_next_goal(tmp_path)

    assert selected.status == "ready"
    assert selected.question_id == "Q-0002"


def test_active_round_blocks_new_goal(tmp_path: Path) -> None:
    _write_programme(tmp_path, [("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "open")
    _write_round(tmp_path, "R7")

    selected = select_next_goal(tmp_path)

    assert selected.status == "blocked-active-round"
    assert selected.active_rounds == ("R7",)
    assert selected.prompt == ""


def test_active_round_on_another_line_does_not_block_selected_line_goal(
    tmp_path: Path,
) -> None:
    _write_programme(tmp_path, [("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "open")
    _write_round(tmp_path, "R7", manuscript_line="line-a")

    selected = select_next_goal(tmp_path, manuscript_line="line-b")

    assert selected.status == "ready"
    assert selected.question_id == "Q-0001"


def test_stale_active_plan_with_verdict_does_not_block(tmp_path: Path) -> None:
    _write_programme(tmp_path, [("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "open")
    _write_round(tmp_path, "R7", verdict=True)

    selected = select_next_goal(tmp_path)

    assert selected.status == "ready"
    assert selected.question_id == "Q-0001"


def test_returns_no_goal_when_all_programme_questions_are_closed(
    tmp_path: Path,
) -> None:
    _write_programme(tmp_path, [("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "closed-positive")

    selected = select_next_goal(tmp_path)

    assert selected.status == "no-eligible-question"
    assert selected.question_id is None


def test_missing_required_reading_fails_loudly(tmp_path: Path) -> None:
    _write_programme(
        tmp_path,
        [("Q-0001", 10)],
        required_reading=["docs/does-not-exist.md"],
    )
    _write_question(tmp_path, "Q-0001", "open")

    with pytest.raises(ProgrammeError, match="required_reading missing"):
        select_next_goal(tmp_path)


def test_unlisted_question_is_not_selected(tmp_path: Path) -> None:
    _write_programme(tmp_path, [("Q-0001", 10)])
    _write_question(tmp_path, "Q-0001", "closed-positive")
    _write_question(tmp_path, "Q-9999", "open")

    selected = select_next_goal(tmp_path)

    assert selected.status == "no-eligible-question"


def test_empty_priority_list_returns_no_goal_not_error(tmp_path: Path) -> None:
    """An empty priority list is a clean no-goal state (2026-07-29 archive cut):
    all closed blocks were moved to RESEARCH_PROGRAM_CLOSED.md, so the live
    programme legitimately has zero listed questions."""
    _write_programme(tmp_path, [])

    selected = select_next_goal(tmp_path)

    assert selected.status == "no-eligible-question"
    assert selected.question_id is None
