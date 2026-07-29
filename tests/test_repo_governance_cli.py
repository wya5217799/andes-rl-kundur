from __future__ import annotations

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
            "allowed": ["README.md", "docs", "memory", "output", "paper", "scripts"],
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
