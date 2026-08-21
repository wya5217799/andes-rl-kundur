"""Windows-safe tests for the R402 capacity-amendment runner."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

amendment = importlib.import_module("run_r402_capacity_amendment")


def _rung(workers, throughput, valid=True):
    return {
        "workers": workers,
        "throughput_jobs_per_second": throughput,
        "maximum_worker_rss_bytes": 1 << 30,
        "all_records_valid": valid,
    }


def test_selects_rung_eight_when_memory_safe():
    rungs = [_rung(1, 1.0), _rung(2, 1.2), _rung(4, 1.5), _rung(8, 2.0)]
    selection = amendment._select_with_training_memory_rule(
        rungs,
        training_worker_rss_bytes=888 * 1024 * 1024,
        wsl_total_bytes=16 * 1024**3,
    )
    assert selection["readiness"] == "RUN-READY"
    assert selection["selected_workers"] == 8
    assert selection["wsl_python_processes"] == 9
    assert selection["host_process_budget"] == 9


def test_falls_back_when_rung_eight_exceeds_memory():
    rungs = [_rung(1, 1.0), _rung(2, 1.2), _rung(4, 1.5), _rung(8, 2.0)]
    selection = amendment._select_with_training_memory_rule(
        rungs,
        training_worker_rss_bytes=900 * 1024 * 1024,
        wsl_total_bytes=8 * 1024**3,
    )
    assert selection["selected_workers"] == 4
    decision = selection["rung_decisions"][3]
    assert decision["reason"] == "training_memory_reserve_guard"


def test_holds_when_nothing_safe():
    rungs = [_rung(1, 1.0, valid=False)]
    selection = amendment._select_with_training_memory_rule(
        rungs,
        training_worker_rss_bytes=888 * 1024 * 1024,
        wsl_total_bytes=16 * 1024**3,
    )
    assert selection["readiness"] == "HOLD"
    assert selection["selected_workers"] is None

