from __future__ import annotations

from copy import deepcopy

from andes_rl_kundur.evaluation.model_first_two_phase_tds_canary import (
    evaluate_two_phase_tds_canary_records,
)


def _record(*, coordinate: str, max_g: float = 1e-10) -> dict[str, object]:
    traces = []
    for step in range(25):
        requested = (
            [0.0, 0.0, -0.05, 0.05]
            if coordinate == "edge_2" and step < 5
            else [0.0] * 4
        )
        traces.append(
            {
                "step": step,
                "t": 0.7 + 0.2 * step,
                "pflow_converged": True,
                "tds_failed": False,
                "system_exit_code": 0,
                "finite_state_algebraic": True,
                "dae_g_residual_max": max_g,
                "vsg_m_actual_system": [300.0] * 4,
                "vsg_d_actual_system": [150.0] * 4,
                "md_write_count": 0,
                "tds_convergence_tolerance": 1e-10,
                "tds_tiny_correction_threshold": 1e-16,
                "tds_solver_transition_count": 1,
                "bess_requested_power_system_pu": requested,
                "line_8_in_service": True,
                "g4_in_service": True,
            }
        )
    return {
        "round": "R309",
        "question": "Q-0065",
        "seal_sha256": "a" * 64,
        "operating_point": "OP1",
        "coordinate": coordinate,
        "sign": "zero" if coordinate == "zero" else "negative",
        "completed": True,
        "tds_failed": False,
        "n_steps": 25,
        "requested_steps": 25,
        "initialization_solver": {
            "method": "trapezoid",
            "convergence_tolerance": 1e-4,
            "tiny_correction_threshold": 1e-10,
            "tds_test_ok": True,
            "system_exit_code": 0,
            "endpoint_seconds": 0.5,
        },
        "structural": {
            "operating_point": {"tie_rx_scale": 1.0, "initial_soc": 0.3},
            "initialization_solver": {
                "method": "trapezoid",
                "convergence_tolerance": 1e-4,
                "tiny_correction_threshold": 1e-10,
                "tds_test_ok": True,
                "system_exit_code": 0,
                "endpoint_seconds": 0.5,
            },
            "solver": {
                "method": "trapezoid",
                "convergence_tolerance": 1e-10,
                "tiny_correction_threshold": 1e-16,
                "transition_count": 1,
                "stopping_semantics": "max_abs_newton_correction",
                "readback_semantics": "post_control_step_recomputed_dae_g",
            },
        },
        "traces": traces,
    }


def _records() -> list[dict[str, object]]:
    return [_record(coordinate="zero"), _record(coordinate="edge_2")]


def test_two_phase_tds_canary_passes_only_execution_gate() -> None:
    result = evaluate_two_phase_tds_canary_records(_records())

    assert result["classification"] == "TWO-PHASE-TDS-CANARY-PASS"
    assert result["fresh_stage1_eligible"] is True
    assert result["predictor_eligible"] is False
    assert result["training_authorized"] is False
    assert result["claim_ceiling"] == "two-phase-solver-validity-only"
    assert all(result["guards"].values())


def test_two_phase_tds_canary_fails_closed_on_initialization() -> None:
    records = deepcopy(_records())
    records[1]["initialization_solver"]["tds_test_ok"] = False

    result = evaluate_two_phase_tds_canary_records(records)

    assert result["classification"] == "INVALID-TWO-PHASE-TDS-CANARY"
    assert result["guards"]["initialization_solver"] is False
    assert result["fresh_stage1_eligible"] is False


def test_two_phase_tds_canary_fails_closed_on_transition_count() -> None:
    records = deepcopy(_records())
    records[0]["traces"][0]["tds_solver_transition_count"] = 2

    result = evaluate_two_phase_tds_canary_records(records)

    assert result["classification"] == "INVALID-TWO-PHASE-TDS-CANARY"
    assert result["guards"]["dynamic_solver_transition"] is False
