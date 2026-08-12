from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "memory"
    / "tools"
    / "technical_route_census.py"
)
SPEC = importlib.util.spec_from_file_location("technical_route_census", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _valid_census(tmp_path: Path) -> dict:
    source = tmp_path / "source.md"
    source.write_text("evidence", encoding="utf-8")
    families = [
        {"id": f"F{number}", "name": f"family {number}", "discriminator": "object"}
        for number in range(1, 6)
    ]
    inventory = [
        {"id": f"T{number}", "name": f"route {number}", "record_refs": ["source.md"]}
        for number in range(1, 6)
    ]
    assignments = []
    for number in range(1, 6):
        assignments.append(
            {
                "route_id": f"T{number}",
                "family": f"F{number}",
                "status": "negative",
                "trained": number == 1,
                "physical_execution": True,
                "genuine_multi_agent": False,
                "implementation_reusable": "partial",
                "evidence_transferable": "bounded-only",
                "title_fit": "partial",
                "headroom": "fail",
                "outcome": "bounded negative result",
                "fatal_boundary": "registered gate failed",
                "next_decisive_gate": "none on this route",
                "eligible": False,
            }
        )
    return {
        "schema_version": 1,
        "line": "example",
        "as_of": "2026-08-13",
        "source_scope": {
            "authoritative_roots": ["source.md"],
            "discovery_method": "read every declared record",
            "excluded_record_classes": ["governance only"],
        },
        "families": families,
        "inventory": inventory,
        "assignments": assignments,
        "coverage": {"inventoried": 5, "assigned": 5, "unresolved_records": []},
        "decision": {
            "outcome": "MANUSCRIPT-ONLY",
            "selected_route": None,
            "reason": "all eligible experiment routes are stopped",
            "authorized_next_action": "draft bounded findings",
            "forbidden_next_actions": ["algorithm sweep"],
        },
    }


def test_valid_census_passes_and_renders_all_families(tmp_path: Path) -> None:
    census = _valid_census(tmp_path)

    result = MODULE.validate_census(census, root=tmp_path)
    rendered = MODULE.render_markdown(census, root=tmp_path)

    assert result["decision"] == "MANUSCRIPT-ONLY"
    assert result["family_counts"] == {f"F{number}": 1 for number in range(1, 6)}
    assert "| T5 | F5 family 5 |" in rendered


def test_missing_assignment_is_rejected(tmp_path: Path) -> None:
    census = _valid_census(tmp_path)
    census["assignments"].pop()
    census["coverage"]["assigned"] = 4

    with pytest.raises(MODULE.CensusError, match="inventory/assignment mismatch"):
        MODULE.validate_census(census, root=tmp_path)


def test_proceed_requires_an_eligible_selected_route(tmp_path: Path) -> None:
    census = _valid_census(tmp_path)
    census["decision"].update(
        {"outcome": "PROCEED", "selected_route": "T1", "reason": "try T1"}
    )

    with pytest.raises(MODULE.CensusError, match="marked eligible"):
        MODULE.validate_census(census, root=tmp_path)


def test_missing_source_pointer_is_rejected(tmp_path: Path) -> None:
    census = _valid_census(tmp_path)
    census["inventory"][0]["record_refs"] = ["missing.md"]

    with pytest.raises(MODULE.CensusError, match="source ref does not exist"):
        MODULE.validate_census(census, root=tmp_path)
