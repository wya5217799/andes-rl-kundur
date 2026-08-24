#!/usr/bin/env python3
"""Validate project skill entrypoints, internal modules, and external skills.

Motivation: location alone cannot resolve overlapping skill triggers. This
checker enforces one repository entrypoint, non-discoverable internal modules,
explicit caller pointers, external invocation policy, and absence of legacy
entrypoint collisions.

Usage:
    python memory/tools/check_skill_scope.py
    python memory/tools/check_skill_scope.py --strict \
      --scope-manifest docs/repo-hygiene/research-skills.scope.json

Failure modes: strict mode exits non-zero for missing, duplicate, misplaced, or
policy-mismatched skills; discoverable/missing/orphan internal modules; global
scope leaks; and discoverable legacy project entrypoint names.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DISCOVERY_NOTICE = (
    "Capability inventory only: AVAILABLE means installed/discovered, "
    "not selected or invoked."
)


def default_roots() -> list[Path]:
    home = Path.home()
    roots = [REPO_ROOT / "skills"]
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        roots.append(Path(codex_home) / "skills")
    roots.extend([home / ".codex" / "skills", home / ".agents" / "skills"])
    unique: list[Path] = []
    for root in roots:
        resolved = root.expanduser().resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def frontmatter_name(skill_file: Path) -> str | None:
    text = skill_file.read_text(encoding="utf-8-sig", errors="replace")
    match = re.search(r"(?m)^name:\s*[\"']?([^\"'\r\n]+)", text)
    return match.group(1).strip() if match else None


def discover(roots: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for skill_file in root.glob("*/SKILL.md"):
            name = frontmatter_name(skill_file)
            if name:
                found.setdefault(name, []).append(str(skill_file.resolve()))
    return found


def invocation_policy(skill_file: Path) -> bool:
    config = skill_file.parent / "agents" / "openai.yaml"
    if not config.is_file():
        return True
    value = yaml.safe_load(config.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        return True
    policy = value.get("policy", {})
    if not isinstance(policy, dict):
        return True
    return policy.get("allow_implicit_invocation", True) is not False


def scope_leaks(skill_file: Path, markers: list[str]) -> list[str]:
    leaks: set[str] = set()
    for path in skill_file.parent.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in {
            ".json",
            ".md",
            ".py",
            ".yaml",
            ".yml",
        }:
            continue
        content = path.read_text(encoding="utf-8-sig", errors="replace")
        for marker in markers:
            if marker.casefold() in content.casefold():
                leaks.add(marker)
    return sorted(leaks)


def require_objects(
    value: Any, field: str, parser: argparse.ArgumentParser
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        parser.error(f"scope manifest {field} must be a list of objects")
    return value


def skill_record(
    *,
    group: str,
    name: str,
    expected_implicit: bool,
    discovered: dict[str, list[str]],
    expected_path: Path | None,
    forbidden_markers: list[str],
) -> dict[str, Any]:
    paths = discovered.get(name, [])
    status = (
        "UNAVAILABLE"
        if not paths
        else "DUPLICATE"
        if len(paths) > 1
        else "MISPLACED"
        if expected_path is not None and Path(paths[0]) != expected_path
        else "AVAILABLE"
    )
    actual = invocation_policy(Path(paths[0])) if len(paths) == 1 else None
    leaks = (
        scope_leaks(Path(paths[0]), forbidden_markers)
        if len(paths) == 1 and group == "external"
        else []
    )
    return {
        "group": group,
        "name": name,
        "availability_status": status,
        "paths": paths,
        "expected_implicit": expected_implicit,
        "actual_implicit": actual,
        "policy_status": (
            "NOT_CHECKED"
            if actual is None
            else "MATCH"
            if actual == expected_implicit
            else "MISMATCH"
        ),
        "scope_status": "LEAK" if leaks else "CLEAN",
        "scope_leaks": leaks,
    }


def module_record(item: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    name = item.get("name")
    relative = item.get("path")
    caller_relative = item.get("caller")
    if not all(isinstance(value, str) for value in (name, relative, caller_relative)):
        raise ValueError("each project module must declare name, path, and caller")
    path = (repo_root / relative).resolve()
    caller = (repo_root / caller_relative).resolve()
    present = path.is_file()
    text = path.read_text(encoding="utf-8-sig", errors="replace") if present else ""
    discoverable = path.name.casefold() == "skill.md" or bool(
        re.search(r"(?m)^name:\s*", text)
    )
    caller_text = (
        caller.read_text(encoding="utf-8-sig", errors="replace")
        if caller.is_file()
        else ""
    )
    referenced = path.name in caller_text
    return {
        "name": name,
        "path": str(path),
        "caller": str(caller),
        "presence_status": "PRESENT" if present else "MISSING",
        "discovery_status": "DISCOVERABLE" if discoverable else "INTERNAL",
        "caller_status": "REFERENCED" if referenced else "ORPHAN",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        action="append",
        type=Path,
        default=[],
        help="Additional direct skill root; may be repeated.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--scope-manifest",
        type=Path,
        default=REPO_ROOT / "docs/repo-hygiene/research-skills.scope.json",
        help="Manifest declaring the project entrypoint, modules, and external skills.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on any scope, placement, discovery, or policy failure.",
    )
    args = parser.parse_args()

    roots = default_roots()
    for root in args.root:
        resolved = root.expanduser().resolve()
        if resolved not in roots:
            roots.append(resolved)
    discovered = discover(roots)

    manifest_path = args.scope_manifest.expanduser().resolve()
    scope = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_root = manifest_path.parents[2]
    project_skills = require_objects(
        scope.get("project_local_skills", []), "project_local_skills", parser
    )
    modules = require_objects(scope.get("project_modules", []), "project_modules", parser)
    external_skills = require_objects(scope.get("global_skills", []), "global_skills", parser)
    forbidden_markers = scope.get("forbidden_global_markers", [])
    if not isinstance(forbidden_markers, list) or not all(
        isinstance(marker, str) for marker in forbidden_markers
    ):
        parser.error("scope manifest forbidden_global_markers must be strings")

    entrypoint_limit = scope.get("selection_contract", {}).get(
        "project_entrypoint_limit", 1
    )
    entrypoint_count_status = (
        "MATCH" if len(project_skills) == entrypoint_limit == 1 else "MISMATCH"
    )

    skill_records: list[dict[str, Any]] = []
    for group, items in (("project", project_skills), ("external", external_skills)):
        for item in items:
            name = item.get("name")
            expected = item.get("allow_implicit_invocation")
            if not isinstance(name, str) or not isinstance(expected, bool):
                parser.error(
                    f"each {group} skill must declare name and allow_implicit_invocation"
                )
            expected_path = None
            if group == "project":
                relative = item.get("path")
                if not isinstance(relative, str):
                    parser.error("each project skill must declare path")
                expected_path = (repo_root / relative / "SKILL.md").resolve()
            skill_records.append(
                skill_record(
                    group=group,
                    name=name,
                    expected_implicit=expected,
                    discovered=discovered,
                    expected_path=expected_path,
                    forbidden_markers=forbidden_markers,
                )
            )

    try:
        module_records = [module_record(item, repo_root) for item in modules]
    except ValueError as exc:
        parser.error(str(exc))

    legacy_names = sorted(
        {
            item["legacy_provenance"]
            for item in modules
            if isinstance(item.get("legacy_provenance"), str)
        }
    )
    legacy_records = [
        {"name": name, "paths": discovered.get(name, [])}
        for name in legacy_names
        if discovered.get(name)
    ]

    payload = {
        "semantics": "capability_inventory_only_not_execution",
        "roots": [str(root) for root in roots],
        "entrypoint_count_status": entrypoint_count_status,
        "skills": skill_records,
        "project_modules": module_records,
        "legacy_entrypoints": legacy_records,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(DISCOVERY_NOTICE)
        print(
            f"{entrypoint_count_status:<12} project-entrypoint-count "
            f"{len(project_skills)}"
        )
        for record in skill_records:
            location = "; ".join(record["paths"]) if record["paths"] else "-"
            print(
                f"{record['availability_status']:<12} {record['group']:<9} "
                f"{record['name']:<36} {record['policy_status']:<10} "
                f"{record['scope_status']:<5} {location}"
            )
        for record in module_records:
            print(
                f"{record['presence_status']:<12} module    {record['name']:<36} "
                f"{record['discovery_status']:<12} {record['caller_status']:<10} "
                f"{record['path']}"
            )
        for record in legacy_records:
            print(
                f"COLLISION    legacy    {record['name']}: "
                f"{'; '.join(record['paths'])}"
            )

    failures = []
    if entrypoint_count_status != "MATCH":
        failures.append("project-entrypoint-count")
    failures.extend(
        record["name"]
        for record in skill_records
        if record["availability_status"] != "AVAILABLE"
        or record["policy_status"] != "MATCH"
        or record["scope_status"] != "CLEAN"
    )
    failures.extend(
        record["name"]
        for record in module_records
        if record["presence_status"] != "PRESENT"
        or record["discovery_status"] != "INTERNAL"
        or record["caller_status"] != "REFERENCED"
    )
    failures.extend(record["name"] for record in legacy_records)
    if failures:
        destination = sys.stderr if args.json else sys.stdout
        print(f"Failures: {', '.join(failures)}", file=destination)
    return 1 if args.strict and failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
