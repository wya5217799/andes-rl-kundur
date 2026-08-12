from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.evaluation.gate_b_deterministic import (
    build_contract,
    classify_summaries,
    controller_spec,
    phase_jobs,
    probe_request,
    project_modes,
    select_development_candidate,
    summarize_arm_records,
    summarize_phase_records,
)


def _frozen_contract_checks(contract) -> None:
    assert contract["round"] == "R376"
    assert contract["steps"] == 50
    assert contract["dt_seconds"] == 0.2
    assert contract["seed"] == 42
    assert contract["probe_component_action"] == 0.25
    assert contract["controller_action_clip"] == 0.70
    assert contract["expected_vsg_idx"] == ["VSG_1", "VSG_2", "VSG_3", "VSG_4"]
    assert contract["expected_vsg_buses"] == [12, 16, 14, 15]
    assert contract["training_authorized"] is False
    assert contract["development"]["record_count"] == 60
    assert contract["evaluation"]["record_count"] == 30
    assert len(contract["distributed_candidates"]) == 4
    assert contract["local_gains"] == {"kp_n_per_hz": 4.0, "ki_n_per_hz_s": 0.8}


def test_build_contract_freezes_gate_b_values() -> None:
    _frozen_contract_checks(build_contract())


def test_phase_jobs_match_frozen_record_counts() -> None:
    contract = build_contract()
    development = phase_jobs("development", contract=contract)
    evaluation = phase_jobs(
        "evaluation",
        selected_arm_id="distributed_feasibility_native_ks1_kc1",
        contract=contract,
    )
    assert len(development) == 60
    assert len(evaluation) == 30
    assert {job["phase"] for job in development} == {"development"}
    assert {job["phase"] for job in evaluation} == {"evaluation"}
    arm_counts = {
        arm: sum(1 for job in development if job["arm_id"] == arm)
        for arm in ("zero_feedback", "local_feasibility_native")
    }
    assert arm_counts == {"zero_feedback": 10, "local_feasibility_native": 10}


def test_evaluation_requires_registered_selected_candidate() -> None:
    with pytest.raises(ValueError):
        phase_jobs("evaluation", contract=build_contract())


def test_probe_request_modes_span_rank_four_within_action_box() -> None:
    contract = build_contract()
    vectors = []
    for mode in contract["mode_ids"]:
        for sign in ("positive", "negative"):
            probe = probe_request(mode, sign, contract=contract)
            assert probe.shape == (4,)
            assert np.all(np.abs(probe) <= 0.25 + 1e-12)
            vectors.append(probe)
    matrix = np.vstack(vectors)
    assert np.linalg.matrix_rank(matrix) == 4


def test_probe_superposition_stays_inside_action_box() -> None:
    contract = build_contract()
    max_magnitude = 0.0
    for mode in contract["mode_ids"]:
        probe = probe_request(mode, "positive", contract=contract)
        max_magnitude = max(max_magnitude, float(np.max(np.abs(probe))))
    assert 0.70 + max_magnitude <= 0.95 + 1e-12


def test_controller_spec_resolves_all_arms() -> None:
    contract = build_contract()
    assert controller_spec("zero_feedback", contract=contract) == {
        "architecture": "zero_feedback"
    }
    assert controller_spec("local_feasibility_native", contract=contract)[
        "architecture"
    ] == "local_feasibility_native"
    for candidate in contract["distributed_candidates"]:
        spec = controller_spec(candidate["arm_id"], contract=contract)
        assert spec["architecture"] == "distributed_feasibility_native"
        assert spec["sync_gain_per_hz"] == candidate["sync_gain_per_hz"]
        assert spec["consensus_gain_per_s"] == candidate["consensus_gain_per_s"]


def test_project_modes_projects_arithmetic_coordinates() -> None:
    contract = build_contract()
    values = np.array(
        [
            [0.01, 0.01, 0.01, 0.01],
            [0.02, 0.02, -0.02, -0.02],
        ]
    )
    projected = project_modes(values, contract=contract)
    assert projected.shape == (2, 4)
    assert np.allclose(projected[:, 0], [0.01, 0.0], atol=1e-12)
    assert np.allclose(projected[:, 1], [0.0, 0.02], atol=1e-12)


def _record(
    *,
    phase: str,
    arm_id: str,
    kind: str,
    condition_id: str,
    input_mode: str | None,
    sign: str | None,
    step_values: dict[str, list],
) -> dict:
    steps = []
    for index in range(50):
        row = {
            "step_index": index,
            "time": 0.2 * index,
            "freq_hz_physical": [60.0] * 4,
            "requested_power_system_pu": [0.0] * 4,
            "commanded_power_system_pu": [0.0] * 4,
            "achieved_power_system_pu": [0.0] * 4,
            "normalized_action": [0.0] * 4,
            "common_action": [0.0] * 4,
            "differential_action": [0.0] * 4,
            "lower_power_system_pu": [-0.1] * 4,
            "upper_power_system_pu": [0.1] * 4,
            "zero_anchor_power_system_pu": [0.0] * 4,
            "feasible_power_system_pu": [0.0] * 4,
            "headroom_fraction": [0.0] * 4,
            "bound_contact": [False] * 4,
            "soc": [0.5] * 4,
            "saturation_reasons": [[], [], [], []],
            "md_action_norm": [[0.0, 0.0]] * 4,
            "tds_failed": False,
        }
        for key, values in step_values.items():
            row[key] = values
        steps.append(row)
    return {
        "phase": phase,
        "arm_id": arm_id,
        "experiment_kind": kind,
        "condition_id": condition_id,
        "delta_u": {},
        "input_mode": input_mode,
        "sign": sign,
        "identity": {
            "n_agents": 4,
            "vsg_idx": ["VSG_1", "VSG_2", "VSG_3", "VSG_4"],
            "vsg_buses": [12, 16, 14, 15],
        },
        "steps": steps,
        "completed_steps": 50,
        "tds_failed": False,
        "failure": None,
        "reward_used_for_gate": False,
        "training_executed": False,
    }


def test_summarize_phase_records_rejects_identity_drift() -> None:
    contract = build_contract()
    records = []
    for job in phase_jobs("development", contract=contract):
        record = _record(
            phase="development",
            arm_id=job["arm_id"],
            kind=job["experiment_kind"],
            condition_id=job["condition_id"],
            input_mode=job["input_mode"],
            sign=job["sign"],
            step_values={},
        )
        record["identity"]["vsg_buses"] = [12, 16, 14, 99]
        records.append(record)
    with pytest.raises(ValueError):
        summarize_phase_records(records, phase="development", contract=contract)


def test_summarize_arm_reports_guards_pass_for_clean_records() -> None:
    contract = build_contract()
    records = []
    for job in phase_jobs("development", contract=contract):
        if job["arm_id"] != "zero_feedback":
            continue
        values = {}
        if job["experiment_kind"] == "probe":
            probe = probe_request(
                job["input_mode"],
                job["sign"],
                contract=contract,
            )
            values = {
                "normalized_action": probe.tolist(),
                "common_action": [float(np.mean(probe))] * 4,
                "differential_action": (probe - np.mean(probe)).tolist(),
            }
        records.append(
            _record(
                phase="development",
                arm_id="zero_feedback",
                kind=job["experiment_kind"],
                condition_id=job["condition_id"],
                input_mode=job["input_mode"],
                sign=job["sign"],
                step_values=values,
            )
        )
    summary = summarize_arm_records(records, contract=contract)
    assert summary["guards_pass"] is True
    assert summary["probe"]["probed_action_rank"] == 4
    assert summary["probe"]["diagonal_response_energy_hz2_s"] == 0.0


def test_summarize_arm_flags_saturation_and_rank_collapse() -> None:
    contract = build_contract()
    records = []
    for job in phase_jobs("development", contract=contract):
        if job["arm_id"] != "zero_feedback":
            continue
        values = {}
        if job["experiment_kind"] == "probe":
            values = {"saturation_reasons": [["ramp"], [], [], []]}
        records.append(
            _record(
                phase="development",
                arm_id="zero_feedback",
                kind=job["experiment_kind"],
                condition_id=job["condition_id"],
                input_mode=job["input_mode"],
                sign=job["sign"],
                step_values=values,
            )
        )
    summary = summarize_arm_records(records, contract=contract)
    assert summary["guards_pass"] is False
    assert any("saturated" in error for error in summary["guard_errors"])


def test_selection_requires_local_baseline_guard_pass() -> None:
    summaries = {
        "local_feasibility_native": {
            "guards_pass": False,
            "probe": {},
            "disturbance": {},
        }
    }
    result = select_development_candidate(summaries, contract=build_contract())
    assert result["classification"] == "ANALYSIS-INVALID"
    assert result["training_authorized"] is False


def _summary_placeholder(guards_pass: bool) -> dict:
    return {
        "guards_pass": guards_pass,
        "probe": {
            "diagonal_response_energy_hz2_s": 1.0,
            "off_diagonal_response_energy_hz2_s": 1.0,
            "off_diagonal_to_diagonal_energy_ratio": 1.0,
        },
        "disturbance": {
            "mean_differential_frequency_energy_hz2_s": 1.0,
            "mean_differential_settling_seconds": 2.0,
            "conditions": {
                "c1": {
                    "differential_frequency_energy_hz2_s": 1.0,
                    "common_frequency_iae_hz_s": 1.0,
                    "worst_device_peak_abs_hz": 1.0,
                    "max_rocof_hz_per_s": 1.0,
                }
            },
        },
    }


def test_classify_returns_stop_when_baseline_guards_fail() -> None:
    development = {
        "classification": "DEVELOPMENT-CANDIDATE-SELECTED",
        "selected_arm_id": "distributed_feasibility_native_ks1_kc1",
    }
    evaluation = {
        "zero_feedback": _summary_placeholder(guards_pass=False),
        "local_feasibility_native": _summary_placeholder(guards_pass=True),
        "distributed_feasibility_native_ks1_kc1": _summary_placeholder(
            guards_pass=True
        ),
    }
    result = classify_summaries(development, evaluation, contract=build_contract())
    assert result["classification"] == "STOP-UNSAFE-CONTROL"
    assert result["training_authorized"] is False
    assert result["next_gate"] is None
