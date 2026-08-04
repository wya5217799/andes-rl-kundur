from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from session_context import (  # noqa: E402
    ContextError,
    ManuscriptContext,
    _manuscript_session,
    build_session_context,
    list_manuscript_lines,
)


def _programme(root: Path) -> None:
    memory = root / "memory"
    (memory / "questions").mkdir(parents=True)
    (memory / "rounds").mkdir()
    (memory / "RESEARCH_PROGRAM.md").write_text(
        "---\n"
        "version: 1\n"
        "status: active\n"
        "programme_id: demo\n"
        "current_phase: P1\n"
        "priority_questions: []\n"
        "---\n"
        "# Programme\n",
        encoding="utf-8",
    )


def _governance_files(root: Path) -> None:
    (root / "skills" / "kundur-round" / "references").mkdir(parents=True)
    (root / "skills" / "kundur-round" / "SKILL.md").write_text("# Round\n", encoding="utf-8")
    (root / "skills" / "kundur-round" / "references" / "resume-contract.md").write_text(
        "# Resume\n",
        encoding="utf-8",
    )
    (root / "CLAUDE.md").write_text("# Rules\n", encoding="utf-8")


def test_line_catalog_lists_active_and_frozen_manuscripts_without_loading_history(
    tmp_path: Path,
) -> None:
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "conference",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/conference",
                    },
                    {
                        "id": "journal",
                        "kind": "manuscript",
                        "status": "frozen",
                        "root": "paper/journal",
                    },
                    {
                        "id": "broken",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/broken",
                    },
                    {
                        "id": "proposal",
                        "kind": "proposal",
                        "status": "active",
                        "root": "paper/proposal",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    conference = tmp_path / "paper" / "conference"
    conference.mkdir(parents=True)
    (conference / "venue.md").write_text("# Venue\n", encoding="utf-8")
    (conference / "LINE.md").write_text(
        "---\n"
        "line_id: conference\n"
        "status: active\n"
        "priority: 1\n"
        "stage: revision\n"
        "objective: Revise conference.\n"
        "artifact_manifest: paper/conference/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots: [paper/conference]\n"
        "  shared_read_roots: []\n"
        "venue:\n"
        "  kind: conference\n"
        "  status: locked\n"
        "  primary: Conference A\n"
        "  decision_record: paper/conference/venue.md\n"
        "  official_source_status: current\n"
        "required_reading: [paper/conference/LINE.md]\n"
        "verification: [Verify.]\n"
        "stop_when: [Done.]\n"
        "---\n",
        encoding="utf-8",
    )
    (conference / "ARTIFACTS.json").write_text(
        '{"version": 1, "line_id": "conference", "artifacts": []}\n',
        encoding="utf-8",
    )
    broken = tmp_path / "paper" / "broken"
    broken.mkdir()
    (broken / "LINE.md").write_text("not frontmatter\n", encoding="utf-8")
    (broken / "ARTIFACTS.json").write_text("{}\n", encoding="utf-8")

    lines = list_manuscript_lines(tmp_path)

    by_id = {line.line_id: line for line in lines}
    assert set(by_id) == {"conference", "journal", "broken"}
    assert by_id["conference"].selectable is True
    assert by_id["conference"].routing_error is None
    assert by_id["journal"].selectable is False
    assert by_id["journal"].routing_error is None
    assert by_id["broken"].selectable is False
    assert by_id["broken"].routing_error is not None
    assert "missing YAML frontmatter" in by_id["broken"].routing_error


def test_no_goal_routes_to_active_manuscript(tmp_path: Path) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    line_root = tmp_path / "paper" / "demo"
    line_root.mkdir(parents=True)
    source = line_root / "source.md"
    source.write_text("# Source\n", encoding="utf-8")
    decision = line_root / "decision.md"
    decision.write_text("# Section 7\n", encoding="utf-8")
    reports = line_root / "reports"
    reports.mkdir()
    feed = reports / "R01.md"
    feed.write_text("# Feed\nCLM-0001\n", encoding="utf-8")
    claim = tmp_path / "memory" / "claims" / "CLM-0001.md"
    claim.parent.mkdir()
    claim.write_text(
        "# Claim\npaper/demo/reports/R01.md\n",
        encoding="utf-8",
    )
    (line_root / "LINE.md").write_text(
        "---\n"
        "line_id: demo-paper\n"
        "status: active\n"
        "priority: 1\n"
        "stage: drafting\n"
        "objective: Draft the results section.\n"
        "artifact_manifest: paper/demo/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots:\n"
        "    - paper/demo\n"
        "  shared_read_roots: []\n"
        "venue:\n"
        "  status: shortlisted\n"
        "  primary: Journal A\n"
        "  backup: Journal B\n"
        "  decision_record: paper/demo/venue.md\n"
        "  official_source_status: partial\n"
        "decision_refs:\n"
        "  - paper/demo/decision.md#Section 7\n"
        "evidence_refs:\n"
        "  - CLM-0001 -> paper/demo/reports/R01.md\n"
        "required_reading:\n"
        "  - paper/demo/LINE.md\n"
        "  - paper/demo/source.md\n"
        "verification:\n"
        "  - Bind every claim to evidence.\n"
        "stop_when:\n"
        "  - The section passes the publication gate.\n"
        "---\n"
        "# Line\n",
        encoding="utf-8",
    )
    (line_root / "ARTIFACTS.json").write_text(
        '{"version": 1, "line_id": "demo-paper", "artifacts": []}\n',
        encoding="utf-8",
    )
    (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "demo-paper",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/demo",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path)

    assert context.mode == "manuscript"
    assert context.objective == "Draft the results section."
    assert context.required_reading == (
        "paper/demo/LINE.md",
        "paper/demo/source.md",
        "paper/demo/ARTIFACTS.json",
    )
    assert context.write_scope == ("paper/demo",)
    assert context.read_scope == ("paper/demo",)
    assert context.venue_status == "shortlisted"
    assert context.primary_venue == "Journal A"
    assert context.decision_refs == ("paper/demo/decision.md#Section 7",)
    assert context.evidence_refs == ("CLM-0001 -> paper/demo/reports/R01.md",)
    assert "paper/demo/decision.md" not in context.required_reading
    assert "paper/demo/reports/R01.md" not in context.required_reading
    assert "memory/claims/CLM-0001.md" not in context.required_reading


def test_active_round_preempts_manuscript(tmp_path: Path) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    round_dir = tmp_path / "memory" / "rounds" / "R01"
    round_dir.mkdir()
    (round_dir / "plan.md").write_text(
        "---\nround: R01\nstate: active\n---\n# Plan\n",
        encoding="utf-8",
    )
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps({"delivery_lines": []}),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path)

    assert context.mode == "resume-round"
    assert context.active_rounds == ("R01",)
    assert "memory/rounds/R01/plan.md" in context.required_reading
    assert (
        "skills/kundur-round/references/resume-contract.md"
        in context.required_reading
    )
    assert "skills/kundur-round/SKILL.md" not in context.required_reading


def test_feed_era_active_state_preempts_even_when_verdict_exists(
    tmp_path: Path,
) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    round_dir = tmp_path / "memory" / "rounds" / "R281"
    round_dir.mkdir()
    (round_dir / "plan.md").write_text(
        "---\nround: R281\nstate: active\n---\n# Plan\n",
        encoding="utf-8",
    )
    (round_dir / "verdict.md").write_text("# Verdict\n", encoding="utf-8")
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps({"delivery_lines": []}),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path)

    assert context.mode == "resume-round"
    assert context.active_rounds == ("R281",)


def test_cold_start_byte_budget_blocks_oversized_required_reading(
    tmp_path: Path,
) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    round_dir = tmp_path / "memory" / "rounds" / "R01"
    round_dir.mkdir()
    (round_dir / "plan.md").write_text(
        "---\nround: R01\nstate: active\n---\n" + ("x" * 4096),
        encoding="utf-8",
    )
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [],
                "manuscript_lines": {
                    "navigation_budgets": {
                        "required_reading_max_bytes": 1024,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ContextError, match="required_reading is .* bytes"):
        build_session_context(tmp_path)


def test_explicit_line_selects_lower_priority_active_manuscript(
    tmp_path: Path,
) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    lines = []
    for line_id, priority in (("primary", 1), ("secondary", 2)):
        line_root = tmp_path / "paper" / line_id
        line_root.mkdir(parents=True)
        (line_root / "ARTIFACTS.json").write_text(
            json.dumps({"version": 1, "line_id": line_id, "artifacts": []}),
            encoding="utf-8",
        )
        (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
        (line_root / "LINE.md").write_text(
            "---\n"
            f"line_id: {line_id}\n"
            "status: active\n"
            f"priority: {priority}\n"
            "stage: drafting\n"
            f"objective: Draft {line_id}.\n"
            f"artifact_manifest: paper/{line_id}/ARTIFACTS.json\n"
            "scope:\n"
            "  write_roots:\n"
            f"    - paper/{line_id}\n"
            "  shared_read_roots: []\n"
            "venue:\n"
            "  status: shortlisted\n"
            "  primary: Journal A\n"
            "  backup: Journal B\n"
            f"  decision_record: paper/{line_id}/venue.md\n"
            "  official_source_status: partial\n"
            "required_reading:\n"
            f"  - paper/{line_id}/LINE.md\n"
            "verification:\n"
            "  - Verify.\n"
            "stop_when:\n"
            "  - Done.\n"
            "---\n",
            encoding="utf-8",
        )
        lines.append(
            {
                "id": line_id,
                "kind": "manuscript",
                "status": "active",
                "root": f"paper/{line_id}",
            }
        )
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps({"delivery_lines": lines}),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path, manuscript_line="secondary")

    assert context.manuscript_line == "secondary"
    assert context.objective == "Draft secondary."
    assert context.write_scope == ("paper/secondary",)


def test_explicit_line_does_not_parse_unselected_active_manuscript(
    tmp_path: Path,
) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    selected = tmp_path / "paper" / "selected"
    selected.mkdir(parents=True)
    (selected / "ARTIFACTS.json").write_text(
        '{"version": 1, "line_id": "selected", "artifacts": []}\n',
        encoding="utf-8",
    )
    (selected / "venue.md").write_text("# Venue\n", encoding="utf-8")
    (selected / "LINE.md").write_text(
        "---\n"
        "line_id: selected\n"
        "status: active\n"
        "priority: 2\n"
        "stage: revision\n"
        "objective: Revise selected.\n"
        "artifact_manifest: paper/selected/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots: [paper/selected]\n"
        "  shared_read_roots: []\n"
        "venue:\n"
        "  status: shortlisted\n"
        "  primary: Journal A\n"
        "  backup: Journal B\n"
        "  decision_record: paper/selected/venue.md\n"
        "  official_source_status: partial\n"
        "required_reading: [paper/selected/LINE.md]\n"
        "verification: [Verify selected.]\n"
        "stop_when: [Selected is complete.]\n"
        "---\n",
        encoding="utf-8",
    )
    broken = tmp_path / "paper" / "broken"
    broken.mkdir()
    (broken / "LINE.md").write_text("not frontmatter\n", encoding="utf-8")
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "broken",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/broken",
                    },
                    {
                        "id": "selected",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/selected",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path, manuscript_line="selected")

    assert context.manuscript_line == "selected"
    assert context.write_scope == ("paper/selected",)


def test_locked_conference_line_does_not_require_transfer_backup(tmp_path: Path) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    (tmp_path / "results").mkdir()
    line_root = tmp_path / "paper" / "conference"
    line_root.mkdir(parents=True)
    (line_root / "ARTIFACTS.json").write_text(
        '{"version": 1, "line_id": "conference", "artifacts": []}\n',
        encoding="utf-8",
    )
    (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
    (line_root / "LINE.md").write_text(
        "---\n"
        "line_id: conference\n"
        "status: active\n"
        "priority: 1\n"
        "stage: revision\n"
        "objective: Revise the accepted conference paper.\n"
        "artifact_manifest: paper/conference/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots: [paper/conference]\n"
        "  shared_read_roots: [memory, results]\n"
        "venue:\n"
        "  kind: conference\n"
        "  status: locked\n"
        "  primary: Conference A\n"
        "  decision_record: paper/conference/venue.md\n"
        "  official_source_status: current\n"
        "required_reading: [paper/conference/LINE.md]\n"
        "verification: [Verify revision scope.]\n"
        "stop_when: [Revision is complete.]\n"
        "---\n",
        encoding="utf-8",
    )
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "conference",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/conference",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path, manuscript_line="conference")

    assert context.manuscript_line == "conference"
    assert context.venue_status == "locked"
    assert context.primary_venue == "Conference A"


def test_manuscript_write_scope_cannot_escape_delivery_root(tmp_path: Path) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    line_root = tmp_path / "paper" / "demo"
    line_root.mkdir(parents=True)
    (line_root / "ARTIFACTS.json").write_text("{}\n", encoding="utf-8")
    (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
    (line_root / "LINE.md").write_text(
        "---\n"
        "line_id: demo\n"
        "status: active\n"
        "priority: 1\n"
        "stage: drafting\n"
        "objective: Draft.\n"
        "artifact_manifest: paper/demo/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots:\n"
        "    - paper/demo\n"
        "    - paper/other\n"
        "  shared_read_roots: []\n"
        "venue:\n"
        "  status: shortlisted\n"
        "  primary: Journal A\n"
        "  backup: Journal B\n"
        "  decision_record: paper/demo/venue.md\n"
        "  official_source_status: partial\n"
        "required_reading:\n"
        "  - paper/demo/LINE.md\n"
        "verification:\n"
        "  - Verify.\n"
        "stop_when:\n"
        "  - Done.\n"
        "---\n",
        encoding="utf-8",
    )
    (tmp_path / "paper" / "other").mkdir()
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "demo",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/demo",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    try:
        build_session_context(tmp_path)
    except ValueError as exc:
        assert "write scope escapes" in str(exc)
    else:
        raise AssertionError("escaping manuscript write scope must fail")


def test_explicit_line_overrides_ready_unreserved_research_goal(
    tmp_path: Path,
) -> None:
    _programme(tmp_path)
    _governance_files(tmp_path)
    question = tmp_path / "memory" / "questions" / "Q-0001.md"
    question.write_text(
        "---\nid: Q-0001\nstatus: open\ntitle: Ready research\nopened_round: R1\n---\n",
        encoding="utf-8",
    )
    required = tmp_path / "docs" / "research.md"
    required.parent.mkdir(parents=True)
    required.write_text("# Research\n", encoding="utf-8")
    programme = tmp_path / "memory" / "RESEARCH_PROGRAM.md"
    programme.write_text(
        "---\n"
        "version: 1\n"
        "status: active\n"
        "programme_id: demo\n"
        "current_phase: P1\n"
        "priority_questions:\n"
        "  - id: Q-0001\n"
        "    rank: 1\n"
        "    phase: P1\n"
        "    objective: Run research.\n"
        "    required_reading:\n"
        "      - docs/research.md\n"
        "    verification:\n"
        "      - Verify research.\n"
        "    scope_limits:\n"
        "      - Stay bounded.\n"
        "    stop_when:\n"
        "      - Research is done.\n"
        "---\n",
        encoding="utf-8",
    )
    line_root = tmp_path / "paper" / "demo"
    line_root.mkdir(parents=True)
    (line_root / "ARTIFACTS.json").write_text(
        '{"version": 1, "line_id": "demo", "artifacts": []}\n',
        encoding="utf-8",
    )
    (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
    (line_root / "LINE.md").write_text(
        "---\n"
        "line_id: demo\n"
        "status: active\n"
        "priority: 1\n"
        "stage: drafting\n"
        "objective: Draft the manuscript.\n"
        "artifact_manifest: paper/demo/ARTIFACTS.json\n"
        "scope:\n"
        "  write_roots: [paper/demo]\n"
        "  shared_read_roots: []\n"
        "venue:\n"
        "  status: shortlisted\n"
        "  primary: Journal A\n"
        "  backup: Journal B\n"
        "  decision_record: paper/demo/venue.md\n"
        "  official_source_status: partial\n"
        "required_reading: [paper/demo/LINE.md]\n"
        "verification: [Verify manuscript.]\n"
        "stop_when: [Manuscript is done.]\n"
        "---\n",
        encoding="utf-8",
    )
    contract = tmp_path / "docs" / "repo-hygiene"
    contract.mkdir(parents=True)
    (contract / "contract.json").write_text(
        json.dumps(
            {
                "delivery_lines": [
                    {
                        "id": "demo",
                        "kind": "manuscript",
                        "status": "active",
                        "root": "paper/demo",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    context = build_session_context(tmp_path, manuscript_line="demo")

    assert context.mode == "manuscript"
    assert context.objective == "Draft the manuscript."


def test_freshness_alert_routes_to_refresh_instead_of_drafting() -> None:
    line = ManuscriptContext(
        line_id="demo",
        line_root="paper/demo",
        priority=1,
        stage="drafting",
        objective="Draft.",
        required_reading=(
            "paper/demo/LINE.md",
            "paper/demo/ARTIFACTS.json",
        ),
        verification=("Verify.",),
        stop_when=("Done.",),
        read_scope=("paper/demo",),
        write_scope=("paper/demo",),
        artifact_manifest="paper/demo/ARTIFACTS.json",
        venue_status="shortlisted",
        primary_venue="Journal A",
        artifact_alerts=("DOCUMENT_INPUT_DRIFT: paper/demo/review.md: source changed",),
    )

    context = _manuscript_session(line)

    assert context.mode == "manuscript-refresh"
    assert context.stage == "artifact-refresh"
    assert context.venue_status == "revalidate"
    assert context.objective.startswith("Refresh or supersede")


def test_missing_navigation_watch_routes_to_refresh_instead_of_drafting() -> None:
    line = ManuscriptContext(
        line_id="demo",
        line_root="paper/demo",
        priority=1,
        stage="drafting",
        objective="Draft.",
        required_reading=(
            "paper/demo/LINE.md",
            "paper/demo/ARTIFACTS.json",
        ),
        verification=("Verify.",),
        stop_when=("Done.",),
        read_scope=("paper/demo",),
        write_scope=("paper/demo",),
        artifact_manifest="paper/demo/ARTIFACTS.json",
        venue_status="shortlisted",
        primary_venue="Journal A",
        artifact_alerts=(
            "DOCUMENT_NAVIGATION_WATCH_MISSING: paper/demo/LINE.md: "
            "line-state does not watch experiment feeds",
        ),
    )

    context = _manuscript_session(line)

    assert context.mode == "manuscript-refresh"
    assert context.stage == "artifact-refresh"


def test_navigation_budget_alert_routes_to_refresh_instead_of_drafting() -> None:
    line = ManuscriptContext(
        line_id="demo",
        line_root="paper/demo",
        priority=1,
        stage="drafting",
        objective="Draft.",
        required_reading=(
            "paper/demo/LINE.md",
            "paper/demo/ARTIFACTS.json",
        ),
        verification=("Verify.",),
        stop_when=("Done.",),
        read_scope=("paper/demo",),
        write_scope=("paper/demo",),
        artifact_manifest="paper/demo/ARTIFACTS.json",
        venue_status="shortlisted",
        primary_venue="Journal A",
        artifact_alerts=("MANUSCRIPT_LINE_BUDGET_EXCEEDED: paper/demo/LINE.md: too long",),
    )

    context = _manuscript_session(line)

    assert context.mode == "manuscript-refresh"
    assert context.stage == "artifact-refresh"
