from __future__ import annotations

from copy import deepcopy

from andes_rl_kundur.evaluation.model_first_tds_canary import (
    evaluate_tds_canary_records,
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
                "bess_requested_power_system_pu": requested,
                "line_8_in_service": True,
                "g4_in_service": True,
            }
        )
    return {
        "round": "R308",
        "question": "Q-0064",
        "seal_sha256": "a" * 64,
        "operating_point": "OP1",
        "coordinate": coordinate,
        "sign": "zero" if coordinate == "zero" else "negative",
        "completed": True,
        "tds_failed": False,
        "n_steps": 25,
        "requested_steps": 25,
        "structural": {
            "operating_point": {
                "tie_rx_scale": 1.0,
                "initial_soc": 0.3,
            },
            "solver": {
                "method": "trapezoid",
                "convergence_tolerance": 1e-10,
                "tiny_correction_threshold": 1e-16,
                "stopping_semantics": "max_abs_newton_correction",
                "readback_semantics": "post_control_step_recomputed_dae_g",
            },
        },
        "traces": traces,
    }


def _records() -> list[dict[str, object]]:
    return [_record(coordinate="zero"), _record(coordinate="edge_2")]


def test_tds_canary_passes_only_solver_diagnosis() -> None:
    result = evaluate_tds_canary_records(_records())

    assert result["classification"] == "TDS-CANARY-PASS"
    assert result["fresh_stage1_eligible"] is True
    assert result["predictor_eligible"] is False
    assert result["training_authorized"] is False
    assert result["claim_ceiling"] == "solver-readback-diagnosis-only"
    assert all(result["guards"].values())


def test_tds_canary_fails_closed_on_unchanged_algebraic_gate() -> None:
    records = _records()
    records[1]["traces"][13]["dae_g_residual_max"] = 1.0000001e-8

    result = evaluate_tds_canary_records(records)

    assert result["classification"] == "INVALID-TDS-CANARY"
    assert result["guards"]["algebraic_residual"] is False
    assert result["fresh_stage1_eligible"] is False
    assert result["training_authorized"] is False


def test_tds_canary_fails_closed_on_solver_readback_drift() -> None:
    records = deepcopy(_records())
    records[0]["traces"][0]["tds_convergence_tolerance"] = 1e-9

    result = evaluate_tds_canary_records(records)

    assert result["classification"] == "INVALID-TDS-CANARY"
    assert result["guards"]["solver_configuration"] is False
