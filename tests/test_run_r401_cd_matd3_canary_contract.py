"""Pure-function tests for the R401 canary-contract runner.

Exercises only the Windows-safe seams (rung selection, contract binding,
job construction).  The WSL rehearse/measure-capacity/prepare commands are
covered by their own rehearsal checks inside the formal path.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

runner = importlib.import_module("run_r401_cd_matd3_canary_contract")


def _rung(workers, throughput, rss_bytes, valid=True):
    return {
        "workers": workers,
        "throughput_jobs_per_second": throughput,
        "maximum_worker_rss_bytes": rss_bytes,
        "all_records_valid": valid,
    }


def test_select_capacity_rung_takes_highest_safe_gain():
    rungs = [
        _rung(1, 1.0, 1 << 30),
        _rung(2, 1.3, 1 << 30),
        _rung(4, 1.6, 1 << 30),
    ]
    selection = runner.select_capacity_rung(
        rungs, wsl_available_bytes=64 << 30
    )
    assert selection["readiness"] == "RUN-READY"
    assert selection["selected_workers"] == 4
    assert selection["wsl_python_processes"] == 5
    assert selection["host_process_budget"] == 5


def test_select_capacity_rung_holds_on_memory_guard():
    rungs = [_rung(1, 1.0, 1 << 30), _rung(2, 1.3, 1 << 30)]
    selection = runner.select_capacity_rung(
        rungs, wsl_available_bytes=3 << 30
    )
    assert selection["readiness"] == "RUN-READY"
    assert selection["selected_workers"] == 1
    assert not selection["rung_decisions"][1]["accepted"]
    assert selection["rung_decisions"][1]["reason"] == "memory_reserve_guard"


def test_select_capacity_rung_holds_when_no_valid_rung():
    rungs = [_rung(1, 1.0, 1 << 30, valid=False)]
    selection = runner.select_capacity_rung(
        rungs, wsl_available_bytes=64 << 30
    )
    assert selection["readiness"] == "HOLD"
    assert selection["selected_workers"] is None


def test_capacity_jobs_use_development_profiles_only():
    contract = runner.build_contract()
    jobs = runner._capacity_jobs(contract)
    assert len(jobs) == 4
    for job in jobs:
        assert job["profile"]["split"] == "development"
        assert job["arm_id"] == "zero"
        assert job["steps_override"] == 30
    profile_ids = {job["profile"]["profile_id"] for job in jobs}
    assert profile_ids == {
        "canary_dev_a",
        "canary_dev_b",
        "canary_dev_c",
        "canary_dev_d",
    }


def test_contract_binding_counts():
    contract = runner.build_contract()
    assert runner.evaluation_record_count(contract) == 240
    assert runner.training_run_count(contract) == 9
    assert runner.TOTAL_INTERACTION_STEPS == 43200
    assert len(contract["profiles"]) == 8

