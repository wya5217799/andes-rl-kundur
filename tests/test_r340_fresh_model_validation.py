from __future__ import annotations

import gzip
import json

import pytest
from probes.r340_fresh_model_validation import classify_r340
from scripts.run_r340_fresh_model_validation import (
    _write_new_gzip_json,
    build_contract,
    candidate_then_bank_schedule,
)


def test_r340_contract_freezes_two_untouched_points_and_exact_66_record_bank() -> None:
    contract = build_contract()

    assert contract["round"] == "R340"
    assert contract["question"] == "Q-0089"
    assert contract["operating_points"] == {
        "HV0": {
            "vsg_m_device": 190.0,
            "vsg_d_device": 95.0,
            "tie_rx_scale": 1.22,
            "initial_soc": 0.46,
        },
        "HV1": {
            "vsg_m_device": 220.0,
            "vsg_d_device": 110.0,
            "tie_rx_scale": 1.45,
            "initial_soc": 0.56,
        },
    }
    assert contract["waveforms"] == {
        "held_pulse_unit": [0.6, 1.0, 1.0, 1.0, 0.6],
        "two_pulse_unit": [1.0, 1.0, 0.0, 0.0, 0.6, 0.6],
    }
    assert contract["amplitudes_system_pu"] == [0.03, 0.07]
    assert contract["record_count_per_point"] == 33
    assert contract["record_count"] == 66
    assert contract["total_steps"] == 1000
    assert contract["validation_horizon_seconds"] == 200.0
    assert contract["estimated_wall_minutes"] == [11.0, 15.0]
    assert contract["candidate_construction"]["order"] == 12
    assert contract["candidate_construction"]["trajectory_fit_count"] == 0
    assert contract["thresholds"] == {
        "nrmse_maximum": 0.15,
        "peak_vector_residual_maximum": 0.20,
    }
    assert contract["controller_executed"] is False
    assert contract["distributed_runtime_executed"] is False
    assert contract["training_executed"] is False


def test_r340_schedule_proves_candidate_persistence_precedes_all_trajectories() -> None:
    schedule = candidate_then_bank_schedule()

    assert schedule["whole_host_python_processes"] == 16
    assert schedule["native_threads_per_process"] == 1
    assert len(schedule["candidate_jobs"]) == 16
    assert schedule["candidate_artifact_create_only"] is True
    assert schedule["validation_seal_binds_candidate_sha256"] is True
    assert schedule["candidate_precedes_every_trajectory"] is True
    assert len(schedule["parent_record_indices"]) == 5
    assert len(schedule["child_record_indices"]) == 61
    assert set(schedule["parent_record_indices"]).isdisjoint(schedule["child_record_indices"])
    assert set(schedule["parent_record_indices"]) | set(schedule["child_record_indices"]) == set(
        range(66)
    )


def test_r340_first_failure_classifier_cannot_promote_a_later_gate() -> None:
    assert (
        classify_r340(
            validity_pass=False,
            construction_pass=True,
            full_linearization_pass=True,
            reduction_pass=True,
        )
        == "INVALID"
    )
    assert (
        classify_r340(
            validity_pass=True,
            construction_pass=False,
            full_linearization_pass=True,
            reduction_pass=True,
        )
        == "BLOCK-CONSTRUCTION"
    )
    assert (
        classify_r340(
            validity_pass=True,
            construction_pass=True,
            full_linearization_pass=False,
            reduction_pass=True,
        )
        == "BLOCK-FULL-LINEARIZATION"
    )
    assert (
        classify_r340(
            validity_pass=True,
            construction_pass=True,
            full_linearization_pass=True,
            reduction_pass=False,
        )
        == "BLOCK-REDUCTION"
    )
    assert (
        classify_r340(
            validity_pass=True,
            construction_pass=True,
            full_linearization_pass=True,
            reduction_pass=True,
        )
        == "ALLOW-MODEL-GATE"
    )


def test_r340_compressed_traces_are_create_only_and_self_hashing(tmp_path) -> None:
    target = tmp_path / "record.json.gz"
    digest = _write_new_gzip_json(target, {"rows": [{"step": 0, "value": 1.5}]})

    assert len(digest) == 64
    assert target.with_suffix(".gz.sha256").read_text(encoding="utf-8").split()[0] == digest
    with gzip.open(target, "rt", encoding="utf-8") as handle:
        assert json.load(handle) == {"rows": [{"step": 0, "value": 1.5}]}
    with pytest.raises(FileExistsError):
        _write_new_gzip_json(target, {"rows": []})
