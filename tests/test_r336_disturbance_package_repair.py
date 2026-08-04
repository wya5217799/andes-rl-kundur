from __future__ import annotations

import subprocess
import sys

from scripts import run_r336_disturbance_package as adapter


def test_successor_changes_identity_only_and_closes_verifier_source() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R336"
    assert contract["question"] == "Q-0086"
    assert contract["record_count"] == 34
    assert contract["parallel_workers_per_split"] == 4
    assert contract["development_fit_holdout_order_remains_serial"] is True
    assert contract["controller_executed"] is False
    assert contract["distributed_runtime_executed"] is False
    assert contract["training_executed"] is False
    assert contract["eval_executed"] is False
    assert contract["title_changed"] is False
    assert adapter._profile_contract(
        channel=None, shape="zero", sign="zero"
    ).event_prefix == "R336_zero"

    sources = adapter._source_paths()
    assert sources["r336_adapter"].name == "run_r336_disturbance_package.py"
    assert sources["r334_adapter"].name == "run_r334_pq_disturbance_identification.py"
    assert adapter._parent_paths()["r335_failure"].is_file()


def test_successor_verifier_accepts_the_registered_case_member(monkeypatch) -> None:
    expected = {
        "andes_version": "2.0.0",
        "installed_sources": {"source.py": "a" * 64},
        "case_sha256": "b" * 64,
    }
    installed = {
        "version": "2.0.0",
        "sources": expected["installed_sources"],
        "case": {"path": "/installed/kundur_full.xlsx", "sha256": "b" * 64},
    }
    monkeypatch.setattr(adapter._r334, "_verify_installed_andes", lambda: installed)

    assert adapter._verify_installed_andes({"expected_runtime": expected}) == installed


def test_successor_cli_bootstraps_from_outside_the_repository(tmp_path) -> None:
    completed = subprocess.run(
        [sys.executable, str(adapter.__file__), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "prepare" in completed.stdout
