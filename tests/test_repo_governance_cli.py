from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = REPO_ROOT / "scripts" / "repo_health.py"


def _write_contract(root: Path, contract: dict[str, object]) -> None:
    policy_dir = root / "docs" / "repo-hygiene"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "contract.json").write_text(
        json.dumps(contract, indent=2),
        encoding="utf-8",
    )


def _contract(**overrides: object) -> dict[str, object]:
    contract: dict[str, object] = {
        "version": 1,
        "baseline": "docs/repo-hygiene/baseline.json",
        "root": {
            "allowed": [
                "README.md",
                "docs",
                "memory",
                "output",
                "paper",
                "results",
                "scripts",
            ],
            "tool_state": [],
        },
        "artifacts": [],
        "navigation": [],
        "opaque_subtrees": [],
    }
    contract.update(overrides)
    return contract


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), "check", "--root", str(root), *args],
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )


def test_repository_tutoring_requires_explicit_invocation() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "Repository tutoring is explicit-only" in agents
    assert "explicitly invokes `$atomic-stem-tutor`" in agents
    assert "ordinary requests to\nunderstand, explain, or interpret" in agents


def test_navigation_adapter_over_budget_reports_finding(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("See docs/source.md\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "source.md").write_text("# Source\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        "one\ntwo\nthree\nfour\nfive\nsix\n", encoding="utf-8"
    )
    _write_contract(
        tmp_path,
        _contract(
            root={"allowed": ["README.md", "CLAUDE.md", "docs"], "tool_state": []},
            navigation=[
                {"adapter": "CLAUDE.md", "max_lines": 3, "must_reference": []}
            ]
        ),
    )
    result = _run(tmp_path, "--format", "json")
    assert result.returncode == 1
    assert "NAV_ADAPTER_OVER_BUDGET" in result.stdout


def test_navigation_adapter_within_budget_passes(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("See docs/source.md\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "source.md").write_text("# Source\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text(
        "one\ntwo\nthree\nfour\nfive\n", encoding="utf-8"
    )
    _write_contract(
        tmp_path,
        _contract(
            root={"allowed": ["README.md", "CLAUDE.md", "docs"], "tool_state": []},
            navigation=[
                {"adapter": "CLAUDE.md", "max_lines": 10, "must_reference": []}
            ]
        ),
    )
    result = _run(tmp_path)
    assert result.returncode == 0


def test_clean_repository_passes_through_the_cli_seam(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("See docs/source.md\n", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "source.md").write_text("# Source\n", encoding="utf-8")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.pdf").write_bytes(b"release")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "release.pdf").write_bytes(b"release")
    _write_contract(
        tmp_path,
        _contract(
            artifacts=[
                {
                    "id": "paper-release",
                    "canonical": "paper/main.pdf",
                    "derived": ["output/release.pdf"],
                    "relation": "byte-identical",
                }
            ],
            navigation=[
                {
                    "adapter": "README.md",
                    "must_reference": ["docs/source.md"],
                }
            ],
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: 0 active finding(s)" in result.stdout
    result.stdout.encode("ascii")


def test_unregistered_root_entry_fails_with_a_stable_rule_id(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "stray.bin").write_bytes(b"unexpected")
    _write_contract(tmp_path, _contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR ROOT_UNDECLARED stray.bin" in result.stdout


def test_baseline_keeps_known_debt_visible_and_stale_entries_fail(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "stray.bin").write_bytes(b"known debt")
    _write_contract(tmp_path, _contract())

    unbaselined = _run(tmp_path, "--format", "json", "--no-baseline")
    report = json.loads(unbaselined.stdout)
    finding = report["findings"][0]
    baseline_path = tmp_path / "docs" / "repo-hygiene" / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "version": 1,
                "findings": [
                    {
                        "fingerprint": finding["fingerprint"],
                        "rule_id": finding["rule_id"],
                        "path": finding["path"],
                        "owner": "repo-owner",
                        "reason": "pre-contract debt",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    baselined = _run(tmp_path)
    assert baselined.returncode == 0
    assert "BASELINED ROOT_UNDECLARED stray.bin" in baselined.stdout

    (tmp_path / "stray.bin").unlink()
    stale = _run(tmp_path)
    assert stale.returncode == 1
    assert "ERROR BASELINE_STALE stray.bin" in stale.stdout


def test_byte_identical_derivation_detects_drift(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.pdf").write_bytes(b"canonical")
    (tmp_path / "output").mkdir()
    (tmp_path / "output" / "release.pdf").write_bytes(b"drifted")
    _write_contract(
        tmp_path,
        _contract(
            artifacts=[
                {
                    "id": "paper-release",
                    "canonical": "paper/main.pdf",
                    "derived": ["output/release.pdf"],
                    "relation": "byte-identical",
                }
            ]
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DERIVED_DRIFT output/release.pdf" in result.stdout


def test_navigation_adapter_must_point_to_an_existing_target(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            navigation=[
                {
                    "adapter": "README.md",
                    "must_reference": ["docs/current.md"],
                }
            ]
        ),
    )

    missing_target = _run(tmp_path)
    assert missing_target.returncode == 1
    assert "ERROR NAV_TARGET_MISSING docs/current.md" in missing_target.stdout

    (tmp_path / "docs" / "current.md").write_text("# Current\n", encoding="utf-8")
    missing_pointer = _run(tmp_path)
    assert missing_pointer.returncode == 1
    assert "ERROR NAV_POINTER_MISSING README.md" in missing_pointer.stdout


def test_delivery_discovery_rejects_an_unregistered_line(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "paper" / "known").mkdir(parents=True)
    (tmp_path / "paper" / "known" / "main.tex").write_text("", encoding="utf-8")
    (tmp_path / "paper" / "surprise").mkdir()
    _write_contract(
        tmp_path,
        _contract(
            delivery_discovery=["paper/*"],
            delivery_lines=[
                {
                    "id": "known",
                    "kind": "manuscript",
                    "status": "active",
                    "root": "paper/known",
                    "roles": {"canonical": ["paper/known/main.tex"]},
                }
            ],
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DELIVERY_UNREGISTERED paper/surprise" in result.stdout


def test_delivery_roles_are_disjoint(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text("", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            delivery_lines=[
                {
                    "id": "paper",
                    "kind": "manuscript",
                    "status": "active",
                    "root": "paper",
                    "roles": {
                        "canonical": ["paper/main.tex"],
                        "derived": ["paper/main.tex"],
                    },
                }
            ]
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DELIVERY_ROLE_CONFLICT paper/main.tex" in result.stdout


def test_delivery_role_paths_must_exist(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "paper").mkdir()
    _write_contract(
        tmp_path,
        _contract(
            delivery_lines=[
                {
                    "id": "paper",
                    "kind": "manuscript",
                    "status": "active",
                    "root": "paper",
                    "roles": {"canonical": ["paper/main.tex"]},
                }
            ]
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DELIVERY_PATH_MISSING paper/main.tex" in result.stdout


def test_unregistered_binary_inside_delivery_root_fails(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "paper").mkdir()
    (tmp_path / "paper" / "main.tex").write_text("", encoding="utf-8")
    (tmp_path / "paper" / "extra.pdf").write_bytes(b"unregistered")
    _write_contract(
        tmp_path,
        _contract(
            delivery_binary_extensions=[".pdf", ".png"],
            delivery_lines=[
                {
                    "id": "paper",
                    "kind": "manuscript",
                    "status": "active",
                    "root": "paper",
                    "roles": {"canonical": ["paper/main.tex"]},
                }
            ],
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DELIVERY_BINARY_UNDECLARED paper/extra.pdf" in result.stdout


def test_new_executable_must_match_a_lifecycle_classifier(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "surprise.py").write_text("print('x')\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            executables={
                "discover": ["scripts/*.py"],
                "classifiers": [],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR EXECUTABLE_UNCLASSIFIED scripts/surprise.py" in result.stdout


def test_lifecycle_classifier_covers_matching_executables(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "repo_check.py").write_text("", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            executables={
                "discover": ["scripts/*.py"],
                "classifiers": [
                    {
                        "pattern": "scripts/repo_check.py",
                        "role": "maintenance",
                        "state": "active",
                        "owner": "repo-governance",
                    }
                ],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout


def test_figure_adapter_must_declare_evidence_that_its_source_references(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    builder = tmp_path / "paper" / "line" / "build_figures.py"
    builder.parent.mkdir(parents=True)
    builder.write_text("print('figure')\n", encoding="utf-8")
    evidence = tmp_path / "results" / "sealed.json"
    evidence.parent.mkdir()
    evidence.write_text("{}\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            executables={
                "discover": ["paper/*/build*.py"],
                "classifiers": [
                    {
                        "pattern": "paper/*/build*.py",
                        "role": "figure-adapter",
                        "state": "frozen",
                        "owner": "paper",
                        "evidence": ["results/sealed.json"],
                    }
                ],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR EXECUTABLE_EVIDENCE_UNREFERENCED paper/line/build_figures.py" in result.stdout


def test_completed_round_marks_active_executable_as_archive_candidate(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "r10_probe.py").write_text("", encoding="utf-8")
    verdict = tmp_path / "memory" / "rounds" / "R10" / "verdict.md"
    verdict.parent.mkdir(parents=True)
    verdict.write_text("**Status**: completed\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            executables={
                "discover": ["scripts/*.py"],
                "classifiers": [
                    {
                        "pattern": "scripts/r*.py",
                        "role": "round-probe",
                        "state": "active",
                        "owner": "round-from-filename",
                    }
                ],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout
    assert "WARN EXECUTABLE_ARCHIVE_CANDIDATE scripts/r10_probe.py" in result.stdout


def test_navigation_adapter_rejects_known_stale_status_copies(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text(
        "## Status (as of 2020-01-01)\n",
        encoding="utf-8",
    )
    _write_contract(
        tmp_path,
        _contract(
            navigation=[
                {
                    "adapter": "README.md",
                    "must_reference": [],
                    "forbid_text": ["Status (as of"],
                }
            ]
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR NAV_FORBIDDEN_TEXT README.md" in result.stdout


def test_future_round_document_budget_blocks_extra_prose(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    round_dir = tmp_path / "memory" / "rounds" / "R287"
    round_dir.mkdir(parents=True)
    (round_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (round_dir / "verdict.md").write_text("# Verdict\n", encoding="utf-8")
    (round_dir / "analysis_notes.md").write_text("# Duplicate prose\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            round_documents={
                "enforce_from": 287,
                "allowed_markdown": ["plan.md", "verdict.md"],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert ("ERROR ROUND_DOCUMENT_UNDECLARED memory/rounds/R287/analysis_notes.md") in result.stdout


def test_round_document_budget_grandfathers_history(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    old_round = tmp_path / "memory" / "rounds" / "R286"
    old_round.mkdir(parents=True)
    (old_round / "historical_notes.md").write_text("# History\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            round_documents={
                "enforce_from": 287,
                "allowed_markdown": ["plan.md", "verdict.md"],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout


def test_external_adapter_lock_cannot_grant_project_write_authority(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    lock_path = tmp_path / "docs" / "external.lock.json"
    lock_path.parent.mkdir()
    lock_path.write_text(
        json.dumps(
            {
                "name": "external-suite",
                "license": "CC-BY-NC-4.0",
                "source_repositories": [
                    {
                        "url": "https://example.test/suite.git",
                        "commit": "abc123",
                    }
                ],
                "project_write_authority": ["claims"],
                "install": {"scope": "global"},
            }
        ),
        encoding="utf-8",
    )
    _write_contract(
        tmp_path,
        _contract(
            external_adapters=[
                {
                    "id": "external-suite",
                    "lock": "docs/external.lock.json",
                    "authority": "explicit-adapter",
                }
            ]
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR EXTERNAL_AUTHORITY_LEAK docs/external.lock.json" in result.stdout


def _active_manuscript_contract() -> dict[str, object]:
    return _contract(
        delivery_lines=[
            {
                "id": "paper-a",
                "kind": "manuscript",
                "status": "active",
                "root": "paper/a",
                "roles": {
                    "canonical": [
                        "paper/a/LINE.md",
                        "paper/a/ARTIFACTS.json",
                    ]
                },
            }
        ],
        manuscript_lines={
            "entry_name": "LINE.md",
            "manifest_name": "ARTIFACTS.json",
            "time_sensitive_purposes": ["venue-decision"],
        },
    )


def _write_manuscript_line(
    root: Path,
    *,
    write_root: str = "paper/a",
    artifacts: list[dict[str, object]] | None = None,
) -> None:
    line_root = root / "paper" / "a"
    line_root.mkdir(parents=True)
    (line_root / "LINE.md").write_text(
        (
            "---\n"
            "line_id: paper-a\n"
            "status: active\n"
            "priority: 1\n"
            "stage: drafting\n"
            "artifact_manifest: paper/a/ARTIFACTS.json\n"
            "scope:\n"
            "  write_roots:\n"
            f"    - {write_root}\n"
            "  shared_read_roots: []\n"
            "venue:\n"
            "  status: shortlisted\n"
            "  primary: Journal A\n"
            "  backup: Journal B\n"
            "  decision_record: paper/a/venue.md\n"
            "  official_source_status: partial\n"
            "required_reading:\n"
            "  - paper/a/LINE.md\n"
            "---\n"
            "# Line\n"
        ),
        encoding="utf-8",
    )
    (line_root / "venue.md").write_text("# Venue\n", encoding="utf-8")
    registered_artifacts = (
        list(artifacts)
        if artifacts is not None
        else [
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            }
        ]
    )
    registered_artifacts.append(
        {
            "id": "venue-record",
            "purpose": "venue-record",
            "path": "paper/a/venue.md",
            "status": "active",
            "canonical": True,
            "authoritative": False,
            "producer": "test",
            "inputs": [],
            "supersedes": [],
            "review_after": None,
        }
    )
    payload = {
        "version": 1,
        "line_id": "paper-a",
        "artifacts": registered_artifacts,
    }
    (line_root / "ARTIFACTS.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_manuscript_write_scope_cannot_escape_delivery_root(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path, write_root="paper")
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_WRITE_SCOPE_ESCAPE paper" in result.stdout


def test_locked_conference_manuscript_does_not_require_transfer_backup(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_text = line_path.read_text(encoding="utf-8")
    line_text = line_text.replace(
        "venue:\n"
        "  status: shortlisted\n"
        "  primary: Journal A\n"
        "  backup: Journal B\n"
        "  decision_record: paper/a/venue.md\n"
        "  official_source_status: partial\n",
        "venue:\n"
        "  kind: conference\n"
        "  status: locked\n"
        "  primary: Conference A\n"
        "  decision_record: paper/a/venue.md\n"
        "  official_source_status: current\n",
    )
    line_text = line_text.replace(
        "required_reading:\n",
        "decision_refs:\n"
        "  - paper/a/venue.md#decision\n"
        "required_reading:\n",
    )
    line_path.write_text(line_text, encoding="utf-8")
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout


def test_round_document_budget_allows_only_exact_retained_path(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    retained = tmp_path / "memory" / "rounds" / "R295"
    future = tmp_path / "memory" / "rounds" / "R296"
    retained.mkdir(parents=True)
    future.mkdir(parents=True)
    name = "consensus_timescale_probe_protocol.md"
    (retained / name).write_text("# Sealed exception\n", encoding="utf-8")
    (future / name).write_text("# Must remain blocked\n", encoding="utf-8")
    _write_contract(
        tmp_path,
        _contract(
            round_documents={
                "enforce_from": 287,
                "allowed_markdown": ["plan.md", "verdict.md"],
                "allowed_paths": [f"R295/{name}"],
            }
        ),
    )

    result = _run(tmp_path)

    assert result.returncode == 1
    assert f"ROUND_DOCUMENT_UNDECLARED memory/rounds/R296/{name}" in result.stdout
    assert f"ROUND_DOCUMENT_UNDECLARED memory/rounds/R295/{name}" not in result.stdout


def test_manuscript_transient_build_files_do_not_require_registration(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_text = line_path.read_text(encoding="utf-8").replace(
        "required_reading:\n",
        "decision_refs:\n"
        "  - paper/a/venue.md#decision\n"
        "required_reading:\n",
    )
    line_path.write_text(line_text, encoding="utf-8")
    (tmp_path / "paper" / "a" / "main.aux").write_text("transient\n", encoding="utf-8")
    cache = tmp_path / "paper" / "a" / "__pycache__"
    cache.mkdir()
    (cache / "builder.pyc").write_bytes(b"transient")
    contract = _active_manuscript_contract()
    manuscript_policy = contract["manuscript_lines"]
    assert isinstance(manuscript_policy, dict)
    manuscript_policy["transient_patterns"] = [
        "**/__pycache__/**",
        "**/*.aux",
    ]
    _write_contract(tmp_path, contract)

    result = _run(tmp_path)

    assert result.returncode == 0, result.stdout


def test_manuscript_evidence_ref_cannot_target_another_line(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    other = tmp_path / "paper" / "other"
    other.mkdir(parents=True)
    feed = other / "R01.md"
    feed.write_text("# Feed\nCLM-0001\n", encoding="utf-8")
    claims = tmp_path / "memory" / "claims"
    claims.mkdir(parents=True)
    (claims / "CLM-0001.md").write_text(
        "# Claim\npaper/other/R01.md\n",
        encoding="utf-8",
    )
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_text = line_path.read_text(encoding="utf-8").replace(
        "required_reading:\n",
        "decision_refs:\n"
        "  - paper/a/venue.md#decision\n"
        "evidence_refs:\n"
        "  - CLM-0001 -> paper/other/R01.md\n"
        "required_reading:\n",
    )
    line_path.write_text(line_text, encoding="utf-8")
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_EVIDENCE_SCOPE_ESCAPE paper/a/LINE.md" in result.stdout


def test_invalid_utf8_manuscript_line_returns_finding_instead_of_traceback(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    line_root = tmp_path / "paper" / "a"
    line_root.mkdir(parents=True)
    (line_root / "LINE.md").write_bytes(b"\xff")
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_LINE_INVALID paper/a/LINE.md" in result.stdout
    assert "Traceback" not in result.stderr


def test_document_manifest_allows_one_active_canonical_per_purpose(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": artifact_id,
                "purpose": "review",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": False,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            }
            for artifact_id in ("review-1", "review-2")
        ],
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_CANONICAL_DUPLICATE" in result.stdout


def test_expired_active_document_blocks_current_use(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "venue",
                "purpose": "venue-decision",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": False,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": "2000-01-01",
            }
        ],
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_REVIEW_EXPIRED paper/a/LINE.md" in result.stdout


def test_active_document_input_hash_drift_blocks_current_use(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    source = tmp_path / "paper" / "source.md"
    source.parent.mkdir()
    source.write_text("new\n", encoding="utf-8")
    old_hash = hashlib.sha256(b"old\n").hexdigest()
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "review",
                "purpose": "review",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": False,
                "producer": "test",
                "inputs": ["paper/source.md"],
                "input_hashes": {"paper/source.md": old_hash},
                "supersedes": [],
                "review_after": None,
            }
        ],
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_INPUT_DRIFT paper/a/LINE.md" in result.stdout


def test_active_document_directory_input_hash_drift_blocks_current_use(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    old_hash = hashlib.sha256(b"old tree").hexdigest()
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": ["paper/a/reports"],
                "input_hashes": {"paper/a/reports": old_hash},
                "supersedes": [],
                "review_after": None,
            },
            {
                "id": "feeds",
                "purpose": "experiment-feeds",
                "path": "paper/a/reports",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
        ],
    )
    reports = tmp_path / "paper" / "a" / "reports"
    reports.mkdir()
    (reports / "R01.md").write_text("# New feed\n", encoding="utf-8")
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_INPUT_DRIFT paper/a/LINE.md" in result.stdout


def test_line_state_must_watch_authoritative_experiment_feed_directory(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
            {
                "id": "feeds",
                "purpose": "experiment-feeds",
                "path": "paper/a/reports",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
        ],
    )
    reports = tmp_path / "paper" / "a" / "reports"
    reports.mkdir()
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_NAVIGATION_WATCH_MISSING paper/a/LINE.md" in result.stdout


def test_required_reading_cannot_eager_load_authoritative_feed(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    old_hash = hashlib.sha256(b"old tree").hexdigest()
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": ["paper/a/reports"],
                "input_hashes": {"paper/a/reports": old_hash},
                "supersedes": [],
                "review_after": None,
            },
            {
                "id": "feeds",
                "purpose": "experiment-feeds",
                "path": "paper/a/reports",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
        ],
    )
    reports = tmp_path / "paper" / "a" / "reports"
    reports.mkdir()
    feed = reports / "R01.md"
    feed.write_text("# Feed\nCLM-0001\n", encoding="utf-8")
    claims = tmp_path / "memory" / "claims"
    claims.mkdir(parents=True)
    (claims / "CLM-0001.md").write_text(
        "# Claim\npaper/a/reports/R01.md\n",
        encoding="utf-8",
    )
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_text = line_path.read_text(encoding="utf-8")
    line_path.write_text(
        line_text.replace(
            "required_reading:\n  - paper/a/LINE.md\n",
            "evidence_refs:\n"
            "  - CLM-0001 -> paper/a/reports/R01.md\n"
            "required_reading:\n"
            "  - paper/a/LINE.md\n"
            "  - paper/a/reports/R01.md\n",
        ),
        encoding="utf-8",
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_EAGER_EVIDENCE_LOAD paper/a/LINE.md" in result.stdout


def test_latest_experiment_feed_must_be_acknowledged_by_evidence_refs(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    old_hash = hashlib.sha256(b"old tree").hexdigest()
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": ["paper/a/reports"],
                "input_hashes": {"paper/a/reports": old_hash},
                "supersedes": [],
                "review_after": None,
            },
            {
                "id": "feeds",
                "purpose": "experiment-feeds",
                "path": "paper/a/reports",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
        ],
    )
    reports = tmp_path / "paper" / "a" / "reports"
    reports.mkdir()
    (reports / "R01.md").write_text("# Feed 1\nCLM-0001\n", encoding="utf-8")
    (reports / "R02.md").write_text("# Feed 2\nCLM-0002\n", encoding="utf-8")
    claims = tmp_path / "memory" / "claims"
    claims.mkdir(parents=True)
    (claims / "CLM-0001.md").write_text(
        "# Claim\npaper/a/reports/R01.md\n",
        encoding="utf-8",
    )
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_text = line_path.read_text(encoding="utf-8")
    line_path.write_text(
        line_text.replace(
            "required_reading:\n",
            "evidence_refs:\n  - CLM-0001 -> paper/a/reports/R01.md\nrequired_reading:\n",
        ),
        encoding="utf-8",
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_NAVIGATION_FRONTIER_STALE paper/a/LINE.md" in result.stdout


def test_manuscript_line_navigation_budget_is_enforced(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_path.write_text(
        line_path.read_text(encoding="utf-8") + ("extra\n" * 20),
        encoding="utf-8",
    )
    contract = _active_manuscript_contract()
    manuscript_policy = contract["manuscript_lines"]
    assert isinstance(manuscript_policy, dict)
    manuscript_policy["navigation_budgets"] = {
        "line_max_lines": 10,
        "line_max_bytes": 1_000_000,
        "required_reading_max_bytes": 1_000_000,
    }
    _write_contract(tmp_path, contract)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_LINE_BUDGET_EXCEEDED paper/a/LINE.md" in result.stdout


def test_manuscript_required_reading_byte_budget_is_enforced(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    source_path = tmp_path / "paper" / "a" / "source.md"
    _write_manuscript_line(
        tmp_path,
        artifacts=[
            {
                "id": "line",
                "purpose": "line-state",
                "path": "paper/a/LINE.md",
                "status": "active",
                "canonical": True,
                "authoritative": True,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
            {
                "id": "source",
                "purpose": "source",
                "path": "paper/a/source.md",
                "status": "active",
                "canonical": True,
                "authoritative": False,
                "producer": "test",
                "inputs": [],
                "supersedes": [],
                "review_after": None,
            },
        ],
    )
    source_path.write_text("x" * 4096, encoding="utf-8")
    line_path = tmp_path / "paper" / "a" / "LINE.md"
    line_path.write_text(
        line_path.read_text(encoding="utf-8").replace(
            "  - paper/a/LINE.md\n",
            "  - paper/a/LINE.md\n  - paper/a/source.md\n",
        ),
        encoding="utf-8",
    )
    contract = _active_manuscript_contract()
    manuscript_policy = contract["manuscript_lines"]
    assert isinstance(manuscript_policy, dict)
    manuscript_policy["navigation_budgets"] = {
        "line_max_lines": 1000,
        "line_max_bytes": 1_000_000,
        "required_reading_max_bytes": 1024,
    }
    _write_contract(tmp_path, contract)

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_CONTEXT_BUDGET_EXCEEDED paper/a/LINE.md" in result.stdout


def test_active_manuscript_requires_lazy_decision_references(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR MANUSCRIPT_DECISION_REFS_MISSING paper/a/LINE.md" in result.stdout


def test_unregistered_durable_file_inside_manuscript_line_fails(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("# Repo\n", encoding="utf-8")
    _write_manuscript_line(tmp_path)
    (tmp_path / "paper" / "a" / "review-final-v2.md").write_text(
        "# Unregistered\n",
        encoding="utf-8",
    )
    _write_contract(tmp_path, _active_manuscript_contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    assert "ERROR DOCUMENT_UNREGISTERED paper/a/review-final-v2.md" in result.stdout


def test_text_findings_are_ascii_safe_for_non_ascii_paths(tmp_path: Path) -> None:
    (tmp_path / "研究").mkdir()
    _write_contract(tmp_path, _contract())

    result = _run(tmp_path)

    assert result.returncode == 1
    result.stdout.encode("ascii")
    assert r"\u7814\u7a76" in result.stdout


def test_real_checkout_passes_repository_health_cli() -> None:
    result = _run(REPO_ROOT)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "OK: 0 active finding(s), 0 baselined" in result.stdout
