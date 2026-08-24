from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCES = REPO_ROOT / "skills/kundur-round/references"
SCRIPT = REPO_ROOT / "memory/tools/check_skill_scope.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_skill_scope", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(name: str) -> str:
    return (REFERENCES / name).read_text(encoding="utf-8")


def run_json(*args: str) -> dict:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_scope_has_one_project_entrypoint_and_internal_modules() -> None:
    payload = run_json("--strict")

    project = [item for item in payload["skills"] if item["group"] == "project"]
    modules = payload["project_modules"]
    assert payload["entrypoint_count_status"] == "MATCH"
    assert [item["name"] for item in project] == ["kundur-round"]
    assert {item["name"] for item in modules} == {
        "research-junction",
        "execution-readiness",
        "evidence-audit",
        "power-systems-audit",
        "submission-audit",
        "skill-maintenance",
    }
    assert all(item["discovery_status"] == "INTERNAL" for item in modules)
    assert all(item["caller_status"] == "REFERENCED" for item in modules)
    assert payload["legacy_entrypoints"] == []


def test_internal_dispatch_defines_exact_triggers_and_collision_owners() -> None:
    routing = read("module-routing.md")

    for marker in (
        "The next research decision or owner is genuinely ambiguous",
        "A non-quick launch, capacity change, ETA",
        "A canonical feed or frozen manuscript claim set needs evidence binding",
        "power-system physics, units, experiment, statistics, or scope review",
        "target venue, article type, and concrete package are all fixed",
        "same canonical feed",
        "Historical artifact `producer` values",
        "one severe failure or a repeated friction pattern",
    ):
        assert marker in routing
    assert "only skill entrypoint" in routing
    assert "not callable entrypoints" in routing


def test_internal_modules_have_no_skill_frontmatter_or_old_entrypoint_links() -> None:
    module_names = (
        "research-junction.md",
        "execution-readiness.md",
        "evidence-audit.md",
        "power-systems-audit.md",
        "submission-audit.md",
    )
    old_paths = (
        "skills/ask-research-supervisor",
        "skills/experiment-efficiency-gate",
        "skills/audit-manuscript-evidence",
        "skills/review-power-systems-manuscript",
        "skills/audit-journal-submission",
    )
    for name in module_names:
        text = read(name)
        normalized = " ".join(text.split())
        assert not text.startswith("---\nname:")
        assert (
            "independently invocable skill" in normalized
            or "skill discovery" in normalized
        )
        assert not any(path in text for path in old_paths)


def test_research_junction_is_advisory_and_cannot_expand_authority() -> None:
    junction = read("research-junction.md")
    normalized = " ".join(junction.split())

    for marker in (
        "frozen active run",
        "one decision question",
        "Direction:",
        "Design:",
        "Readiness:",
        "Result:",
        "Claim:",
    ):
        assert marker in junction
    assert "owns route-card grammar only" in junction
    assert "does not by itself supply new authority" in normalized
    assert "Treat a frozen active run as monitor-only" in junction


def test_execution_readiness_keeps_capacity_mechanics_bounded() -> None:
    readiness = read("execution-readiness.md")
    junction_bundle = "\n".join(
        (read("research-experiment-protocol.md"), read("routing-map.md"))
    )

    assert "This module checks execution readiness only" in readiness
    for detail in ("capacity ladder", "waves = ceil", "2–60 minutes"):
        assert detail in readiness
        assert detail not in junction_bundle
    assert "A plumbing check is not capacity evidence" in " ".join(readiness.split())


def test_publication_modules_have_disjoint_returns() -> None:
    routing = read("module-routing.md")
    gate = read("publication-gate.md")

    assert "Evidence audit owns traceability" in routing
    assert "Power-system audit owns domain validity" in routing
    assert "Submission audit owns current venue mechanics only" in routing
    assert gate.index("evidence-audit.md") < gate.index("power-systems-audit.md")


def test_discover_reports_duplicate_capabilities(tmp_path: Path) -> None:
    module = load_module()
    for folder in ("first", "second"):
        skill_dir = tmp_path / folder
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: duplicate-skill\ndescription: test\n---\n",
            encoding="utf-8",
        )
    assert len(module.discover([tmp_path])["duplicate-skill"]) == 2


def test_explicit_only_policy_is_read_from_openai_yaml(tmp_path: Path) -> None:
    module = load_module()
    skill_dir = tmp_path / "explicit-skill"
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        "---\nname: explicit-skill\ndescription: test\n---\n",
        encoding="utf-8",
    )
    (agents_dir / "openai.yaml").write_text(
        "policy:\n  allow_implicit_invocation: false\n", encoding="utf-8"
    )
    assert module.invocation_policy(skill_file) is False


def test_module_record_rejects_discoverable_or_orphan_module(tmp_path: Path) -> None:
    module = load_module()
    module_path = tmp_path / "SKILL.md"
    module_path.write_text("---\nname: bad-module\n---\n", encoding="utf-8")
    caller = tmp_path / "router.md"
    caller.write_text("no pointer here\n", encoding="utf-8")

    record = module.module_record(
        {"name": "bad", "path": "SKILL.md", "caller": "router.md"}, tmp_path
    )
    assert record["discovery_status"] == "DISCOVERABLE"
    assert record["caller_status"] == "ORPHAN"
