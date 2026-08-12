"""Validate a temporary five-family technical-route census.

Motivation
----------
When this repository has many historical controllers but no clear next
experiment, prose summaries tend to omit failed branches or silently promote
reusable code into transferable evidence.  This validator makes the semantic
classification reviewable: an agent first inventories route *episodes*, then
assigns every inventoried episode exactly once to one of the five project
families and records a terminal route decision.

The census is navigation, not experimental evidence.  Keep normal outputs in
``tmp/<line>/``; claims, feeds, results, and manuscript LINE files remain the
authoritative sources.

Usage
-----
    python memory/tools/technical_route_census.py validate \
        tmp/<line>/technical-route-census.json
    python memory/tools/technical_route_census.py render \
        tmp/<line>/technical-route-census.json

Failure modes
-------------
The command exits 2 for malformed JSON, missing source pointers, an incomplete
or duplicate assignment, an unknown family/status, or a decision inconsistent
with the classified eligibility.  It never modifies the census or repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FAMILY_IDS = {"F1", "F2", "F3", "F4", "F5"}
ROUTE_STATUSES = {
    "positive",
    "negative",
    "mixed",
    "legacy",
    "pretraining-stop",
    "prospective",
}
DECISIONS = {"PROCEED", "MANUSCRIPT-ONLY", "UNRESOLVED"}
REUSE_VALUES = {"yes", "partial", "no"}
TRANSFER_VALUES = {"yes", "bounded-only", "no"}
TITLE_FIT_VALUES = {"yes", "partial", "no"}
HEADROOM_VALUES = {"pass", "fail", "unknown", "not-applicable"}


class CensusError(ValueError):
    """A human-correctable census contract violation."""


def _require_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CensusError(f"{context}: {key} must be non-empty text")
    return value.strip()


def _require_list(mapping: dict[str, Any], key: str, context: str) -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value:
        raise CensusError(f"{context}: {key} must be a non-empty list")
    return value


def _check_repo_ref(ref: str, context: str, root: Path) -> None:
    path_text = ref.split("#", 1)[0]
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts:
        raise CensusError(f"{context}: source ref must be repo-relative: {ref}")
    if not (root / path).exists():
        raise CensusError(f"{context}: source ref does not exist: {ref}")


def load_census(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CensusError(f"cannot read census {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CensusError("census root must be a JSON object")
    return value


def validate_census(data: dict[str, Any], *, root: Path = ROOT) -> dict[str, Any]:
    """Validate structure, source reachability, coverage, and final decision."""

    if data.get("schema_version") != 1:
        raise CensusError("schema_version must be 1")
    _require_text(data, "line", "census")
    _require_text(data, "as_of", "census")

    source_scope = data.get("source_scope")
    if not isinstance(source_scope, dict):
        raise CensusError("source_scope must be an object")
    roots = _require_list(source_scope, "authoritative_roots", "source_scope")
    for ref in roots:
        if not isinstance(ref, str):
            raise CensusError("source_scope: authoritative_roots must contain text")
        _check_repo_ref(ref, "source_scope", root)
    _require_text(source_scope, "discovery_method", "source_scope")
    _require_list(source_scope, "excluded_record_classes", "source_scope")

    families = data.get("families")
    if not isinstance(families, list):
        raise CensusError("families must be a list")
    family_ids: list[str] = []
    for index, family in enumerate(families):
        context = f"families[{index}]"
        if not isinstance(family, dict):
            raise CensusError(f"{context}: must be an object")
        family_id = _require_text(family, "id", context)
        family_ids.append(family_id)
        _require_text(family, "name", context)
        _require_text(family, "discriminator", context)
    if set(family_ids) != FAMILY_IDS or len(family_ids) != len(FAMILY_IDS):
        raise CensusError("families must define F1..F5 exactly once")

    inventory = data.get("inventory")
    if not isinstance(inventory, list) or not inventory:
        raise CensusError("inventory must be a non-empty list")
    inventory_ids: list[str] = []
    for index, route in enumerate(inventory):
        context = f"inventory[{index}]"
        if not isinstance(route, dict):
            raise CensusError(f"{context}: must be an object")
        route_id = _require_text(route, "id", context)
        inventory_ids.append(route_id)
        _require_text(route, "name", context)
        refs = _require_list(route, "record_refs", context)
        for ref in refs:
            if not isinstance(ref, str):
                raise CensusError(f"{context}: record_refs must contain text")
            _check_repo_ref(ref, context, root)
    if len(inventory_ids) != len(set(inventory_ids)):
        raise CensusError("inventory route ids must be unique")

    assignments = data.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise CensusError("assignments must be a non-empty list")
    assignment_ids: list[str] = []
    eligible_routes: set[str] = set()
    family_counts = {family_id: 0 for family_id in FAMILY_IDS}
    for index, assignment in enumerate(assignments):
        context = f"assignments[{index}]"
        if not isinstance(assignment, dict):
            raise CensusError(f"{context}: must be an object")
        route_id = _require_text(assignment, "route_id", context)
        assignment_ids.append(route_id)
        family_id = _require_text(assignment, "family", context)
        if family_id not in FAMILY_IDS:
            raise CensusError(f"{context}: unknown family {family_id}")
        family_counts[family_id] += 1

        status = _require_text(assignment, "status", context)
        if status not in ROUTE_STATUSES:
            raise CensusError(f"{context}: unknown status {status}")
        for key in ("trained", "physical_execution", "genuine_multi_agent", "eligible"):
            if not isinstance(assignment.get(key), bool):
                raise CensusError(f"{context}: {key} must be boolean")
        for key, allowed in (
            ("implementation_reusable", REUSE_VALUES),
            ("evidence_transferable", TRANSFER_VALUES),
            ("title_fit", TITLE_FIT_VALUES),
            ("headroom", HEADROOM_VALUES),
        ):
            value = _require_text(assignment, key, context)
            if value not in allowed:
                raise CensusError(f"{context}: invalid {key} value {value}")
        _require_text(assignment, "outcome", context)
        _require_text(assignment, "fatal_boundary", context)
        _require_text(assignment, "next_decisive_gate", context)
        if assignment["eligible"]:
            eligible_routes.add(route_id)

    if len(assignment_ids) != len(set(assignment_ids)):
        raise CensusError("each inventoried route may be assigned only once")
    missing = sorted(set(inventory_ids) - set(assignment_ids))
    extra = sorted(set(assignment_ids) - set(inventory_ids))
    if missing or extra:
        raise CensusError(f"inventory/assignment mismatch: missing={missing}, extra={extra}")
    empty_families = sorted(key for key, count in family_counts.items() if count == 0)
    if empty_families:
        raise CensusError(f"every family must contain a route: empty={empty_families}")

    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        raise CensusError("coverage must be an object")
    if coverage.get("inventoried") != len(inventory_ids):
        raise CensusError("coverage.inventoried must equal inventory length")
    if coverage.get("assigned") != len(assignment_ids):
        raise CensusError("coverage.assigned must equal assignment length")
    unresolved = coverage.get("unresolved_records")
    if not isinstance(unresolved, list):
        raise CensusError("coverage.unresolved_records must be a list")

    decision = data.get("decision")
    if not isinstance(decision, dict):
        raise CensusError("decision must be an object")
    outcome = _require_text(decision, "outcome", "decision")
    if outcome not in DECISIONS:
        raise CensusError(f"decision: unknown outcome {outcome}")
    _require_text(decision, "reason", "decision")
    _require_text(decision, "authorized_next_action", "decision")
    _require_list(decision, "forbidden_next_actions", "decision")
    selected = decision.get("selected_route")
    if outcome == "PROCEED":
        if selected not in eligible_routes:
            raise CensusError("PROCEED must select one route marked eligible")
        if unresolved:
            raise CensusError("PROCEED is forbidden while unresolved records remain")
    elif outcome == "MANUSCRIPT-ONLY":
        if selected is not None:
            raise CensusError("MANUSCRIPT-ONLY must not select an experiment route")
        if unresolved:
            raise CensusError("MANUSCRIPT-ONLY is forbidden while records remain unresolved")
    else:
        if not unresolved:
            raise CensusError("UNRESOLVED requires at least one unresolved record")
        if selected is not None:
            raise CensusError("UNRESOLVED must not select an experiment route")

    return {
        "line": data["line"],
        "routes": len(inventory_ids),
        "family_counts": dict(sorted(family_counts.items())),
        "eligible_routes": sorted(eligible_routes),
        "decision": outcome,
    }


def render_markdown(data: dict[str, Any], *, root: Path = ROOT) -> str:
    """Render a compact human review table after successful validation."""

    validation = validate_census(data, root=root)
    inventory = {item["id"]: item for item in data["inventory"]}
    families = {item["id"]: item["name"] for item in data["families"]}
    lines = [
        f"# Technical-route census — {validation['line']}",
        "",
        f"As of: {data['as_of']}",
        "",
        "| ID | Family | Route | Outcome | Title fit | Headroom | Eligible |",
        "|---|---|---|---|---|---|---|",
    ]
    for assignment in data["assignments"]:
        route = inventory[assignment["route_id"]]
        eligible = "yes" if assignment["eligible"] else "no"
        lines.append(
            f"| {assignment['route_id']} | {assignment['family']} "
            f"{families[assignment['family']]} | {route['name']} | "
            f"{assignment['outcome']} | {assignment['title_fit']} | "
            f"{assignment['headroom']} | {eligible} |"
        )
    decision = data["decision"]
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"**{decision['outcome']}** — {decision['reason']}",
            "",
            f"Authorized next action: {decision['authorized_next_action']}",
            "",
            "This is a navigation audit, not experimental evidence.",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "render"):
        child = subparsers.add_parser(command)
        child.add_argument("census", type=Path)
    args = parser.parse_args(argv)
    try:
        data = load_census(args.census)
        if args.command == "validate":
            result = validate_census(data)
            print("PASS " + json.dumps(result, ensure_ascii=False, sort_keys=True))
        else:
            print(render_markdown(data), end="")
    except CensusError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
