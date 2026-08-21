from __future__ import annotations

import scripts.run_r399_md_decoupling_headroom as runner


def test_runner_contract_matches_pure_scientific_contract() -> None:
    contract = runner.build_contract()

    assert len(contract["profiles"]) == 6
    assert len(contract["arm_ids"]) == 10
    assert runner.formal_job_count(contract) == 360
    assert contract["training_authorized"] is False


def test_capacity_selection_uses_throughput_and_memory_guards() -> None:
    rungs = [
        {
            "workers": 1,
            "all_records_valid": True,
            "throughput_jobs_per_second": 1.0,
            "maximum_worker_rss_bytes": 100,
        },
        {
            "workers": 2,
            "all_records_valid": True,
            "throughput_jobs_per_second": 1.8,
            "maximum_worker_rss_bytes": 100,
        },
        {
            "workers": 4,
            "all_records_valid": True,
            "throughput_jobs_per_second": 1.85,
            "maximum_worker_rss_bytes": 100,
        },
    ]

    decision = runner.select_capacity_rung(rungs, wsl_available_bytes=1_000)

    assert decision["selected_workers"] == 2
    assert decision["host_process_budget"] == 3
    assert decision["wsl_python_processes"] == 3
    assert decision["readiness"] == "RUN-READY"
    assert decision["rung_decisions"][-1]["accepted"] is False
    assert decision["rung_decisions"][-1]["reason"] == "insufficient_throughput_gain"


def test_rehearsal_requires_all_preattempt_checks_and_no_physical_trace() -> None:
    checks = {
        "source_hash": True,
        "parent_hash": True,
        "installed_package": True,
        "installed_case": True,
        "output_absence": True,
        "active_plan": True,
        "active_line": True,
        "contract_closed": True,
        "physical_trajectory_executed": False,
    }

    assert runner.rehearsal_checks_pass(checks) is True
    checks["installed_case"] = False
    assert runner.rehearsal_checks_pass(checks) is False


def test_capacity_schema_upgrade_preserves_measurements_and_adds_host_budget() -> None:
    original = {
        "schema_version": 1,
        "round": "R399",
        "readiness": "RUN-READY",
        "host_process_budget": 5,
        "wsl_python_processes": 5,
        "selected_workers": 4,
        "rungs": [{"workers": 4, "wall_seconds": 4.0}],
        "sources": {"runner": {"sha256": "old"}},
        "parents": {"route": {"sha256": "parent"}},
        "installed_runtime": {"andes_version": "2.0.0"},
    }
    snapshot = {
        "sources": {"runner": {"sha256": "new"}},
        "parents": {"route": {"sha256": "parent"}},
        "installed_runtime": {"andes_version": "2.0.0"},
    }

    corrected = runner.upgrade_capacity_payload(
        original,
        snapshot=snapshot,
        original_path="memory/rounds/R399/capacity_evidence.json",
        original_sha256="abc123",
    )

    assert corrected["schema_version"] == 2
    assert corrected["whole_host_python_process_budget"] == 5
    assert corrected["rungs"] == original["rungs"]
    assert corrected["sources"] == snapshot["sources"]
    assert corrected["empirical_anchor"] == {
        "all_records_valid": True,
        "concurrent_workers": 5,
        "simulator_workers": 4,
        "launcher_processes": 1,
        "native_threads_per_worker": 1,
        "source": "selected representative capacity rung",
    }
    assert corrected["physical_capacity_rerun_executed"] is False
    assert corrected["supersedes_capacity"]["sha256"] == "abc123"
