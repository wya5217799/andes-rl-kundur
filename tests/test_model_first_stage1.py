from __future__ import annotations

from copy import deepcopy

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    stage1_operating_points,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)
from andes_rl_kundur.evaluation.model_first_stage1 import (
    evaluate_stage1_records,
    paired_response_metrics,
)


def test_paired_response_metrics_separate_signal_nonlinearity_and_cross_gain() -> None:
    zero = np.zeros((2, 4), dtype=float)
    positive = np.asarray(
        [
            [1.0, 3.0, 0.0, 0.0],
            [2.0, 4.0, 0.0, 0.0],
        ]
    )
    negative = -positive
    input_trace = np.ones((2, 4), dtype=float)

    common = paired_response_metrics(
        zero,
        positive,
        negative,
        input_trace=input_trace,
        input_kind="common",
    )
    edge = paired_response_metrics(
        zero,
        positive,
        negative,
        input_trace=input_trace,
        input_kind="edge",
    )

    assert common["midpoint_nonlinearity_ratio"] == 0.0
    assert common["signal_to_baseline_drift_ratio"] > 1e12
    assert common["self_gain"] == np.linalg.norm([1.0, 2.0]) / np.sqrt(8.0)
    assert common["cross_gain"] == 5.0 / np.sqrt(8.0)
    assert edge["cross_gain"] == common["self_gain"]
    assert edge["self_gain"] == common["cross_gain"]


def _eval_scorecard(*, passed: bool = True) -> dict[str, object]:
    return {
        "validity": {
            "diagnostic_pass": passed,
            "input_integrity": {"pass": passed},
            "execution_contract": {"pass": passed},
        },
        "evidence_status": {
            "status": "EXTERNAL_AUTHORITY_REQUIRED",
            "eligible": None,
        },
        "source": {"trace_count": 18},
    }


def _stage1_records() -> list[dict[str, object]]:
    coordinates = stage1_power_coordinates()
    records: list[dict[str, object]] = []
    for point in stage1_operating_points():
        transform = weighted_common_differential_transform(
            np.full(4, point.vsg_m_system)
        )
        for coordinate in ("zero", *coordinates):
            signs = ("zero",) if coordinate == "zero" else ("positive", "negative")
            for sign in signs:
                sign_value = {"zero": 0.0, "positive": 1.0, "negative": -1.0}[sign]
                pulse = (
                    np.zeros(4)
                    if coordinate == "zero"
                    else sign_value * coordinates[coordinate]
                )
                traces: list[dict[str, object]] = []
                cumulative_power = np.zeros(4)
                for step in range(25):
                    requested = pulse if step < 5 else np.zeros(4)
                    cumulative_power += requested
                    xi = np.zeros(4)
                    if coordinate != "zero":
                        response = sign_value * 1e-3 * np.exp(-0.08 * step)
                        if coordinate == "common":
                            xi[0] = response
                            xi[1] = 0.2 * response
                        else:
                            edge_index = int(coordinate[-1])
                            xi[0] = 0.1 * response
                            xi[edge_index + 1] = response
                    omega_deviation = transform.inverse @ xi
                    delta_f = 60.0 * omega_deviation
                    soc = point.initial_soc - 1e-4 * cumulative_power
                    internal = {
                        "Pext0": requested.tolist(),
                        "Psum": requested.tolist(),
                        "Ipul": requested.tolist(),
                        "Ipcmd_y": requested.tolist(),
                        "Ipout_y": requested.tolist(),
                        "Ipmin": [-1.0] * 4,
                        "Ipmax": [1.0] * 4,
                        "Fvl": [1.0] * 4,
                        "Fvh": [1.0] * 4,
                        "Ffl": [1.0] * 4,
                        "Ffh": [1.0] * 4,
                    }
                    traces.append(
                        {
                            "step": step,
                            "t": 0.7 + 0.2 * step,
                            "delta_f_physical_hz": delta_f.tolist(),
                            "freq_hz_physical": (60.0 + delta_f).tolist(),
                            "action_norm": [[0.0, 0.0] for _ in range(4)],
                            "bess_requested_power_system_pu": requested.tolist(),
                            "bess_commanded_power_system_pu": requested.tolist(),
                            "bess_external_command_readback_system_pu": requested.tolist(),
                            "bess_internal_power_reference_system_pu": requested.tolist(),
                            "bess_actual_power_system_pu": requested.tolist(),
                            "bess_soc": soc.tolist(),
                            "bess_charge_energy_mwh_total": [0.0] * 4,
                            "bess_discharge_energy_mwh_total": [0.0] * 4,
                            "bess_constraint_violations": [],
                            "bess_saturation_reasons": [[], [], [], []],
                            "bess_internal": internal,
                            "vsg_m_actual_system": [point.vsg_m_system] * 4,
                            "vsg_d_actual_system": [point.vsg_d_system] * 4,
                            "md_write_count": 0,
                            "pflow_converged": True,
                            "tds_failed": False,
                            "system_exit_code": 0,
                            "finite_state_algebraic": True,
                            "dae_g_residual_max": 1e-10,
                            "line_8_in_service": True,
                            "g4_in_service": True,
                            "g4_m_actual_system": 111.15,
                        }
                    )
                records.append(
                    {
                        "round": "R307",
                        "question": "Q-0063",
                        "seal_sha256": "a" * 64,
                        "operating_point": point.name,
                        "coordinate": coordinate,
                        "sign": sign,
                        "initial_soc": point.initial_soc,
                        "completed": True,
                        "tds_failed": False,
                        "n_steps": 25,
                        "requested_steps": 25,
                        "traces": traces,
                    }
                )
    return records


def test_stage1_valid_records_pass_authority_but_never_authorize_training() -> None:
    result = evaluate_stage1_records(_stage1_records(), _eval_scorecard())

    assert result["classification"] == "STAGE1-PASS"
    assert result["predictor_eligible"] is True
    assert result["training_authorized"] is False
    assert all(result["guards"].values())
    assert len(result["pair_metrics"]) == 12
    assert result["max_op0_nonlinearity_ratio"] == 0.0
    assert result["max_all_nonlinearity_ratio"] == 0.0
    assert result["common_to_differential_gains"]
    assert result["differential_to_common_gains"]


def test_stage1_valid_but_nonlinear_records_fail_as_authority_no_go() -> None:
    records = _stage1_records()
    target = next(
        record
        for record in records
        if record["operating_point"] == "OP0"
        and record["coordinate"] == "edge_0"
        and record["sign"] == "positive"
    )
    for row in target["traces"]:
        row["delta_f_physical_hz"] = [0.6, 0.6, 0.6, 0.6]
        row["freq_hz_physical"] = [60.6, 60.6, 60.6, 60.6]

    result = evaluate_stage1_records(records, _eval_scorecard())

    assert result["classification"] == "STAGE1-AUTHORITY-NO-GO"
    assert result["guards"]["paired_local_linearity"] is False
    assert result["training_authorized"] is False


def test_stage1_eval_integrity_failure_invalidates_execution() -> None:
    result = evaluate_stage1_records(_stage1_records(), _eval_scorecard(passed=False))

    assert result["classification"] == "INVALID-STAGE1-EXECUTION"
    assert result["guards"]["eval_diagnostic_integrity"] is False
    assert result["training_authorized"] is False


def _fresh_two_phase_records() -> list[dict[str, object]]:
    records = deepcopy(_stage1_records())
    initialization = {
        "method": "trapezoid",
        "convergence_tolerance": 1e-4,
        "tiny_correction_threshold": 1e-10,
        "tds_test_ok": True,
        "system_exit_code": 0,
        "endpoint_seconds": 0.5,
    }
    solver = {
        "method": "trapezoid",
        "convergence_tolerance": 1e-10,
        "tiny_correction_threshold": 1e-16,
        "transition_count": 1,
        "stopping_semantics": "max_abs_newton_correction",
        "readback_semantics": "post_control_step_recomputed_dae_g",
    }
    for record in records:
        record["round"] = "R310"
        record["question"] = "Q-0066"
        record["initialization_solver"] = deepcopy(initialization)
        record["structural"] = {
            "initialization_solver": deepcopy(initialization),
            "solver": deepcopy(solver),
        }
        for row in record["traces"]:
            row["tds_convergence_tolerance"] = 1e-10
            row["tds_tiny_correction_threshold"] = 1e-16
            row["tds_solver_transition_count"] = 1
    return records


def test_fresh_stage1_requires_and_passes_two_phase_solver_contract() -> None:
    result = evaluate_stage1_records(
        _fresh_two_phase_records(),
        _eval_scorecard(),
        expected_round="R310",
        expected_question="Q-0066",
        require_two_phase_solver=True,
    )

    assert result["classification"] == "STAGE1-PASS"
    assert result["guards"]["two_phase_solver_contract"] is True
    assert result["predictor_eligible"] is True
    assert result["training_authorized"] is False


def test_fresh_stage1_fails_closed_on_solver_transition_drift() -> None:
    records = _fresh_two_phase_records()
    records[0]["traces"][0]["tds_solver_transition_count"] = 2

    result = evaluate_stage1_records(
        records,
        _eval_scorecard(),
        expected_round="R310",
        expected_question="Q-0066",
        require_two_phase_solver=True,
    )

    assert result["classification"] == "INVALID-STAGE1-EXECUTION"
    assert result["guards"]["two_phase_solver_contract"] is False
    assert result["predictor_eligible"] is False
