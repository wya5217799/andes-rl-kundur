from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "probes/r303_projection_coupling.py"
SPEC = importlib.util.spec_from_file_location("r303_probe", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
r303 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r303)


def test_registered_matrix_is_complete_and_fail_closed_for_training() -> None:
    summary = r303.analyze_projection_coupling()

    assert summary["case_count"] == 32
    assert summary["guards"]["all_pass"] is True
    assert summary["classification"] in {
        "PROJECTION-SEAM-PRESERVED",
        "PROJECTION-LEAKAGE-IMMATERIAL",
        "COUPLING-CLASSICALLY-CLOSED",
        "LOCAL-CLASSICAL-GAP",
        "COORDINATE-REPAIR-FAILED",
    }
    assert summary["training_gate"]["authorized"] is False
    assert summary["training_gate"]["training_executed"] is False
    assert summary["eval_gate"]["status"] == "NOT-APPLICABLE-NO-TRACE"
    assert summary["title_alignment"]["supports_marl_term"] is False
    assert summary["title_alignment"]["actuator_matches_vsg_term"] is False


def test_classifier_preserves_all_preregistered_outcomes() -> None:
    assert r303.classify_projection_probe(
        guards_pass=False,
        mechanism_case_count=3,
        material_case_count=2,
        local_valid=True,
        local_sufficient=True,
    ) == "INVALID-PROJECTION-PROBE"
    assert r303.classify_projection_probe(
        guards_pass=True,
        mechanism_case_count=0,
        material_case_count=0,
        local_valid=True,
        local_sufficient=True,
    ) == "PROJECTION-SEAM-PRESERVED"
    assert r303.classify_projection_probe(
        guards_pass=True,
        mechanism_case_count=4,
        material_case_count=1,
        local_valid=True,
        local_sufficient=True,
    ) == "PROJECTION-LEAKAGE-IMMATERIAL"
    assert r303.classify_projection_probe(
        guards_pass=True,
        mechanism_case_count=4,
        material_case_count=2,
        local_valid=True,
        local_sufficient=True,
    ) == "COUPLING-CLASSICALLY-CLOSED"
    assert r303.classify_projection_probe(
        guards_pass=True,
        mechanism_case_count=4,
        material_case_count=2,
        local_valid=True,
        local_sufficient=False,
    ) == "LOCAL-CLASSICAL-GAP"
    assert r303.classify_projection_probe(
        guards_pass=True,
        mechanism_case_count=4,
        material_case_count=2,
        local_valid=False,
        local_sufficient=False,
    ) == "COORDINATE-REPAIR-FAILED"


def test_probe_writes_canonical_json_and_matching_sidecar(tmp_path: Path) -> None:
    output = tmp_path / "analysis_summary.json"
    assert r303.main(["--output", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    sidecar = output.with_suffix(".json.sha256")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    assert payload["round"] == "R303"
    assert sidecar.read_text(encoding="ascii") == f"{digest}  {output.name}\n"
    with pytest.raises(FileExistsError):
        r303.main(["--output", str(output)])


def test_probe_cli_runs_from_repository_without_installed_package(tmp_path: Path) -> None:
    output = tmp_path / "cli_summary.json"
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(output.read_text(encoding="utf-8"))["round"] == "R303"


def test_analyzer_classifies_local_candidate_failure_without_invalidating_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = r303.allocate_edge_flows_with_headroom

    def violate_local_zero_sum(**kwargs):
        result = original(**kwargs)
        command = result.commanded_power_system_pu.copy()
        residual = result.residual_power_system_pu.copy()
        command[0] += 0.001
        residual[0] += 0.001
        return replace(
            result,
            commanded_power_system_pu=command,
            residual_power_system_pu=residual,
        )

    monkeypatch.setattr(r303, "allocate_edge_flows_with_headroom", violate_local_zero_sum)
    summary = r303.analyze_projection_coupling()

    assert summary["guards"]["core_all_pass"] is True
    assert summary["guards"]["local_all_valid"] is False
    assert summary["classification"] == "COORDINATE-REPAIR-FAILED"
    assert summary["training_gate"]["authorized"] is False
    assert np.isfinite(summary["aggregate"]["max_independent_common_leakage_abs_system_pu"])
