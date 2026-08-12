from __future__ import annotations

from pathlib import Path

import pytest

from scripts.run_r367_deterministic_headroom import (
    _build_capacity_payload,
    _rehearsal_checks,
    _write_new_json,
)


def test_create_only_json_writer_hashes_and_refuses_replacement(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"

    digest = _write_new_json(path, {"b": 2, "a": 1})

    assert path.read_text(encoding="utf-8") == '{"a":1,"b":2}'
    assert path.with_name("artifact.json.sha256").read_text(encoding="ascii") == (
        f"{digest}  artifact.json\n"
    )
    with pytest.raises(FileExistsError):
        _write_new_json(path, {"a": 1})


def test_rehearsal_requires_same_entry_checks_without_a_physical_trace() -> None:
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "in_flight_question": True,
        "contract_closed": True,
        "physical_trajectory_executed": False,
    }

    assert _rehearsal_checks({"checks": checks}) is True
    assert _rehearsal_checks({"checks": {**checks, "source_hash": False}}) is False
    assert _rehearsal_checks(
        {"checks": {**checks, "physical_trajectory_executed": True}}
    ) is False


def test_capacity_payload_is_serial_measured_and_never_authorizes_training() -> None:
    payload = _build_capacity_payload(
        representative_valid=True,
        representative_wall_seconds=2.0,
        max_rss_kib=1234,
        disk_free_bytes=10_000,
        logical_processors=8,
        physical_memory_bytes=20_000,
        wsl_memory_available_bytes=15_000,
        runtime={"andes_version": "demo"},
        sources={"runner": {"sha256": "abc"}},
        parents={"design_claim": {"sha256": "def"}},
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["whole_host_python_process_budget"] == 1
    assert payload["host_process_budget"] == 1
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["other_reserved_processes"] == 0
    assert payload["empirical_anchor"]["representative_steps"] == 5
    assert payload["projected_formal_wall_seconds"] == 960.0
    assert payload["scientific_classification_inspected"] is False
    assert payload["training_executed"] is False
