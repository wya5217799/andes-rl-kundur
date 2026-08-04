from __future__ import annotations

import numpy as np
from probes.r324_model_fidelity_validation import (
    REQUIRED_PARAMETER_IDS,
    evaluate_model_fidelity,
)


def _binding(identifier: str) -> dict[str, object]:
    return {
        "id": identifier,
        "value": "fixture",
        "unit": "declared",
        "base": "declared",
        "represented_object": "fixture object",
        "source_locator": "fixture/source#locator",
        "provenance_class": "explicit-modelling-assumption",
        "binding_status": "bound",
        "physically_calibrated": False,
        "calibration_ceiling": "not measured or physically calibrated",
    }


def _trace(substeps: int, offset: float = 0.0) -> dict[str, object]:
    time = 0.5 + 0.2 * np.arange(1, 26)
    pulse = np.asarray([0.0, 0.0, -0.05, 0.05])
    actual = np.zeros((25, 4))
    actual[:5] = pulse
    actual[5:10] = np.linspace(0.8, 0.0, 5)[:, None] * pulse
    actual += offset
    requested = np.zeros((25, 4))
    requested[:5] = pulse
    frequency = np.full((25, 4), 60.0)
    frequency[:, 0] += np.linspace(0.0, 0.01, 25) + offset
    soc = np.full((25, 4), 0.5)
    soc[:, 2] += np.linspace(0.0, 1e-4, 25) + offset * 1e-3
    soc[:, 3] -= np.linspace(0.0, 1e-4, 25) + offset * 1e-3
    return {
        "substeps": substeps,
        "max_segment_seconds": 0.2 / substeps,
        "operating_point": "OP0",
        "coordinate": "edge_2",
        "sign": "negative",
        "completed": True,
        "execution_guard_failures": [],
        "time_seconds": time.tolist(),
        "achieved_power_system_pu": actual.tolist(),
        "frequency_hz": frequency.tolist(),
        "soc": soc.tolist(),
        "requested_power_system_pu": requested.tolist(),
        "commanded_power_system_pu": requested.tolist(),
        "external_command_readback_system_pu": requested.tolist(),
        "vsg_m_actual_system": np.full((25, 4), 400.0).tolist(),
        "vsg_d_actual_system": np.full((25, 4), 200.0).tolist(),
        "dae_g_residual_max": np.zeros(25).tolist(),
        "pflow_converged": [True] * 25,
        "tds_failed": [False] * 25,
        "system_exit_code": [0] * 25,
        "finite_state_algebraic": [True] * 25,
        "line_8_in_service": [True] * 25,
        "g4_in_service": [True] * 25,
        "md_write_count": [0] * 25,
        "external_saturation_active": [False] * 25,
        "internal_limiter_active": [False] * 25,
        "constraint_violation_count": [0] * 25,
        "tds_method": "trapezoid",
        "initialization_tolerance": 1e-4,
        "initialization_tiny_correction_threshold": 1e-10,
        "dynamic_tolerance": 1e-10,
        "dynamic_tiny_correction_threshold": 1e-16,
        "terminal_x": [1.0 + offset, 0.1],
        "terminal_y": [0.9, -0.2 + offset],
    }


def _payload() -> dict[str, object]:
    return {
        "round": "R324",
        "question": "Q-0079",
        "seal_sha256": "a" * 64,
        "parameter_bindings": [
            _binding(identifier) for identifier in sorted(REQUIRED_PARAMETER_IDS)
        ],
        "traces": [_trace(5), _trace(10, 1e-5), _trace(20, 1.2e-5)],
        "physical_execution_performed": True,
        "controller_executed": False,
        "closed_loop_executed": False,
        "eval_status": "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE",
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }


def test_r324_passes_only_when_inventory_execution_and_both_pairs_pass() -> None:
    analysis = evaluate_model_fidelity(_payload())

    assert analysis["classification"] == "MODEL-FIDELITY-GATE-PASS"
    assert analysis["gates"]["parameter_provenance"] is True
    assert analysis["gates"]["all_adjacent_refinements"] is True
    assert len(analysis["adjacent_comparisons"]) == 2


def test_r324_reports_time_step_no_go_for_one_failed_adjacent_pair() -> None:
    payload = _payload()
    payload["traces"][0] = _trace(5, 0.01)  # type: ignore[index]

    analysis = evaluate_model_fidelity(payload)

    assert analysis["classification"] == "TIME-STEP-CONVERGENCE-NO-GO"
    assert analysis["gates"]["parameter_provenance"] is True
    assert analysis["gates"]["all_adjacent_refinements"] is False


def test_r324_reports_parameter_no_go_without_reading_convergence_as_pass() -> None:
    payload = _payload()
    payload["parameter_bindings"][0]["binding_status"] = "unbound"  # type: ignore[index]

    analysis = evaluate_model_fidelity(payload)

    assert analysis["classification"] == "PARAMETER-PROVENANCE-NO-GO"
    assert analysis["gates"]["parameter_provenance"] is False


def test_r324_invalidity_precedes_parameter_and_convergence_metrics() -> None:
    payload = _payload()
    payload["traces"][1]["execution_guard_failures"] = ["tds_failed"]  # type: ignore[index]

    analysis = evaluate_model_fidelity(payload)

    assert analysis["classification"] == "INVALID-MODEL-FIDELITY-CHECK"
    assert analysis["adjacent_comparisons"] == []
