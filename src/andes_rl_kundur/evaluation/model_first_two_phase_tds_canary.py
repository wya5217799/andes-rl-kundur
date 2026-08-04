"""Fail-closed evaluation for the R309 two-phase TDS canary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

INITIALIZATION_TOLERANCE = 1e-4
INITIALIZATION_TOL_ZERO = 1e-10
DYNAMIC_TOLERANCE = 1e-10
DYNAMIC_TOL_ZERO = 1e-16
ALGEBRAIC_RESIDUAL_MAX = 1e-8
EXPECTED_STEPS = 25
ACTIVE_STEPS = 5


def _finite_vector(value: object, *, size: int = 4) -> np.ndarray | None:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.shape != (size,) or not np.all(np.isfinite(array)):
        return None
    return array


def _expected_request(coordinate: str, step: int) -> np.ndarray:
    if coordinate == "zero" or step >= ACTIVE_STEPS:
        return np.zeros(4)
    return np.asarray([0.0, 0.0, -0.05, 0.05])


def evaluate_two_phase_tds_canary_records(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify the exact OP1 zero plus edge-2-negative R309 bank."""

    expected_identities = {("zero", "zero"), ("edge_2", "negative")}
    identities = {
        (str(record.get("coordinate")), str(record.get("sign")))
        for record in records
    }
    guards: dict[str, bool] = {
        "identity_and_trace_count": (
            len(records) == 2
            and identities == expected_identities
            and all(
                record.get("round") == "R309"
                and record.get("question") == "Q-0065"
                and record.get("operating_point") == "OP1"
                and isinstance(record.get("seal_sha256"), str)
                and len(str(record.get("seal_sha256"))) == 64
                for record in records
            )
        ),
        "initialization_solver": True,
        "dynamic_solver_transition": True,
        "sample_count_and_time_grid": True,
        "pflow_tds_exit": True,
        "finite_state_algebraic": True,
        "algebraic_residual": True,
        "input_contract": True,
        "md_readback_and_writes": True,
        "structural_execution": True,
    }
    max_g = 0.0
    trace_maxima: dict[str, float] = {}

    for record in records:
        coordinate = str(record.get("coordinate"))
        sign = str(record.get("sign"))
        initialization = record.get("initialization_solver", {})
        guards["initialization_solver"] &= (
            isinstance(initialization, Mapping)
            and initialization.get("method") == "trapezoid"
            and initialization.get("convergence_tolerance")
            == INITIALIZATION_TOLERANCE
            and initialization.get("tiny_correction_threshold")
            == INITIALIZATION_TOL_ZERO
            and initialization.get("tds_test_ok") is True
            and initialization.get("system_exit_code") == 0
            and isinstance(initialization.get("endpoint_seconds"), (int, float))
            and abs(float(initialization.get("endpoint_seconds", 0.0)) - 0.5)
            <= 1e-9
        )

        traces = record.get("traces")
        if not isinstance(traces, list):
            traces = []
        guards["sample_count_and_time_grid"] &= (
            record.get("completed") is True
            and record.get("tds_failed") is False
            and record.get("n_steps") == EXPECTED_STEPS
            and record.get("requested_steps") == EXPECTED_STEPS
            and len(traces) == EXPECTED_STEPS
        )

        structural = record.get("structural")
        solver = structural.get("solver", {}) if isinstance(structural, Mapping) else {}
        operating_point = (
            structural.get("operating_point", {})
            if isinstance(structural, Mapping)
            else {}
        )
        structural_initialization = (
            structural.get("initialization_solver", {})
            if isinstance(structural, Mapping)
            else {}
        )
        guards["initialization_solver"] &= structural_initialization == initialization
        guards["dynamic_solver_transition"] &= (
            solver.get("method") == "trapezoid"
            and solver.get("convergence_tolerance") == DYNAMIC_TOLERANCE
            and solver.get("tiny_correction_threshold") == DYNAMIC_TOL_ZERO
            and solver.get("transition_count") == 1
            and solver.get("stopping_semantics") == "max_abs_newton_correction"
            and solver.get("readback_semantics")
            == "post_control_step_recomputed_dae_g"
        )
        guards["structural_execution"] &= (
            operating_point.get("tie_rx_scale") == 1.0
            and operating_point.get("initial_soc") == 0.3
        )

        local_max = 0.0
        for index, row in enumerate(traces):
            if not isinstance(row, Mapping):
                guards["sample_count_and_time_grid"] = False
                continue
            expected_time = 0.7 + 0.2 * index
            guards["sample_count_and_time_grid"] &= (
                row.get("step") == index
                and isinstance(row.get("t"), (int, float))
                and abs(float(row.get("t", 0.0)) - expected_time) <= 1e-9
            )
            guards["pflow_tds_exit"] &= (
                row.get("pflow_converged") is True
                and row.get("tds_failed") is False
                and row.get("system_exit_code") == 0
            )
            guards["finite_state_algebraic"] &= (
                row.get("finite_state_algebraic") is True
            )
            try:
                residual = float(row.get("dae_g_residual_max"))
            except (TypeError, ValueError):
                residual = float("inf")
            guards["algebraic_residual"] &= (
                np.isfinite(residual) and residual <= ALGEBRAIC_RESIDUAL_MAX
            )
            local_max = max(local_max, residual)
            max_g = max(max_g, residual)
            guards["dynamic_solver_transition"] &= (
                row.get("tds_convergence_tolerance") == DYNAMIC_TOLERANCE
                and row.get("tds_tiny_correction_threshold") == DYNAMIC_TOL_ZERO
                and row.get("tds_solver_transition_count") == 1
            )

            request = _finite_vector(row.get("bess_requested_power_system_pu"))
            guards["input_contract"] &= (
                request is not None
                and np.allclose(
                    request,
                    _expected_request(coordinate, index),
                    rtol=0.0,
                    atol=1e-12,
                )
            )
            m_actual = _finite_vector(row.get("vsg_m_actual_system"))
            d_actual = _finite_vector(row.get("vsg_d_actual_system"))
            guards["md_readback_and_writes"] &= (
                row.get("md_write_count") == 0
                and m_actual is not None
                and d_actual is not None
                and np.allclose(m_actual, 300.0, rtol=0.0, atol=1e-10)
                and np.allclose(d_actual, 150.0, rtol=0.0, atol=1e-10)
            )
            guards["structural_execution"] &= (
                row.get("line_8_in_service") is True
                and row.get("g4_in_service") is True
            )
        trace_maxima[f"OP1/{coordinate}/{sign}"] = local_max

    passed = all(guards.values())
    return {
        "classification": (
            "TWO-PHASE-TDS-CANARY-PASS"
            if passed
            else "INVALID-TWO-PHASE-TDS-CANARY"
        ),
        "guards": guards,
        "max_dae_g_residual": max_g,
        "trace_max_dae_g_residual": trace_maxima,
        "fresh_stage1_eligible": passed,
        "predictor_eligible": False,
        "controller_development_authorized": False,
        "training_authorized": False,
        "claim_ceiling": "two-phase-solver-validity-only",
    }
