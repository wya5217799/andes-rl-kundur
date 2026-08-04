"""R292 completion-screen audit for the frozen q0 physical contract.

The generic prospective-authority screen historically audits a storage-zero,
constant-inertia baseline.  R292 instead freezes the validated droop--PI BESS
layer and a 15-step common-inertia pulse.  This module validates that distinct
contract without inspecting any frequency-performance endpoint.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.control.vector_inertia_residual import (
    r292_vector_residual_contract,
)

R292_SCREEN_STEPS = 300
R292_BESS_POWER_MAX_SYSTEM_PU = 0.36
R292_SOC_MIN = 0.20
R292_SOC_MAX = 0.80


def _flatten(traces: list[Mapping[str, Any]], field: str) -> np.ndarray:
    return np.asarray(
        [value for step in traces for value in step.get(field, [])],
        dtype=float,
    )


def _max_abs(values: np.ndarray) -> float:
    return float(np.max(np.abs(values))) if values.size else 0.0


def _exact_profile(
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    atol: float = 1e-7,
) -> bool:
    return bool(
        actual.shape == expected.shape
        and np.all(np.isfinite(actual))
        and np.allclose(actual, expected, rtol=0.0, atol=atol)
    )


def audit_r292_q0_screen_record(
    record: Mapping[str, Any],
    *,
    trace_sha256: str,
) -> dict[str, Any]:
    """Reduce one raw q0 trace to completion and frozen-physics evidence."""
    contract = r292_vector_residual_contract()
    traces = list(record.get("traces", []))
    frequency = np.asarray(
        [step.get("freq_hz_physical", []) for step in traces], dtype=float
    )
    action = np.asarray(
        [step.get("action_norm", []) for step in traces], dtype=float
    )
    m_values = np.asarray([step.get("M_es", []) for step in traces], dtype=float)
    d_values = np.asarray([step.get("D_es", []) for step in traces], dtype=float)
    edge = np.asarray(
        [step.get("r292_edge_flow_norm", []) for step in traces], dtype=float
    )
    node = np.asarray(
        [step.get("r292_node_residual_norm", []) for step in traces], dtype=float
    )
    physical_sum = np.asarray(
        [step.get("r292_physical_m_residual_sum", np.nan) for step in traces],
        dtype=float,
    )
    requested = _flatten(traces, "bess_requested_power_system_pu")
    commanded = _flatten(traces, "bess_commanded_power_system_pu")
    actual = _flatten(traces, "bess_actual_power_system_pu")
    soc = _flatten(traces, "bess_soc")
    voltage = _flatten(traces, "bess_bus_voltage_pu")
    violations = [
        violation
        for step in traces
        for violation in step.get("bess_constraint_violations", [])
    ]
    saturation_reasons = [
        reason
        for step in traces
        for reason in step.get("bess_saturation_reasons", [])
    ]

    expected_action = np.zeros((R292_SCREEN_STEPS, 4, 2), dtype=float)
    expected_action[: contract.active_steps, :, 0] = contract.common_amplitude
    expected_m = np.full(
        (R292_SCREEN_STEPS, 4), contract.baseline_m, dtype=float
    )
    expected_m[: contract.active_steps] = (
        contract.baseline_m + contract.dm_max * contract.common_amplitude
    )
    expected_d = np.full(
        (R292_SCREEN_STEPS, 4), contract.baseline_d, dtype=float
    )
    zero_edge = np.zeros((R292_SCREEN_STEPS, contract.edge_count), dtype=float)
    zero_node = np.zeros((R292_SCREEN_STEPS, contract.agent_count), dtype=float)
    finite_bess = all(
        values.size == R292_SCREEN_STEPS * contract.agent_count
        and np.all(np.isfinite(values))
        for values in (requested, commanded, actual, soc, voltage)
    )
    checks = {
        "controller_q0": record.get("controller") == "q0",
        "complete_300_steps": bool(
            record.get("completed")
            and not record.get("tds_failed")
            and int(record.get("requested_steps", -1)) == R292_SCREEN_STEPS
            and int(record.get("n_steps", -1)) == R292_SCREEN_STEPS
            and len(traces) == R292_SCREEN_STEPS
        ),
        "physical_60hz_schema": bool(
            frequency.shape == (R292_SCREEN_STEPS, contract.agent_count)
            and np.all(np.isfinite(frequency))
            and float(record.get("andes_nominal_frequency_hz", 60.0)) == 60.0
        ),
        "common_action_profile": _exact_profile(action, expected_action),
        "m_profile": _exact_profile(m_values, expected_m, atol=1e-5),
        "d_profile": _exact_profile(d_values, expected_d, atol=1e-7),
        "zero_edge_residual": _exact_profile(edge, zero_edge),
        "zero_node_residual": _exact_profile(node, zero_node),
        "physical_residual_zero_sum": bool(
            physical_sum.shape == (R292_SCREEN_STEPS,)
            and np.all(np.isfinite(physical_sum))
            and np.max(np.abs(physical_sum)) <= 1e-4
        ),
        "bess_schema_finite": bool(finite_bess),
        "bess_power_bounds": bool(
            finite_bess
            and max(
                _max_abs(requested),
                _max_abs(commanded),
                _max_abs(actual),
            )
            <= R292_BESS_POWER_MAX_SYSTEM_PU + 1e-12
        ),
        "soc_bounds": bool(
            finite_bess
            and float(np.min(soc)) >= R292_SOC_MIN - 1e-9
            and float(np.max(soc)) <= R292_SOC_MAX + 1e-9
        ),
        "zero_constraint_violations": not violations,
        "zero_saturation_reasons": not any(bool(row) for row in saturation_reasons),
        "trace_sha256_shape": bool(
            len(trace_sha256) == 64
            and all(character in "0123456789abcdef" for character in trace_sha256)
        ),
    }
    m_unique = sorted(set(m_values.reshape(-1).tolist())) if m_values.size else []
    d_unique = sorted(set(d_values.reshape(-1).tolist())) if d_values.size else []
    return {
        "scenario": str(record["scenario"]),
        "plant": "r292_q0_common_pulse_plus_droop_pi",
        "delta_u": dict(record["delta_u"]),
        "completed": bool(record.get("completed")),
        "tds_failed": bool(record.get("tds_failed")),
        "n_steps": int(record.get("n_steps", 0)),
        "requested_steps": int(record.get("requested_steps", 0)),
        "physical_valid": all(checks.values()),
        "checks": checks,
        "max_abs_requested_power": _max_abs(requested),
        "max_abs_commanded_power": _max_abs(commanded),
        "max_abs_actual_power": _max_abs(actual),
        "min_soc": float(np.min(soc)) if soc.size else None,
        "max_soc": float(np.max(soc)) if soc.size else None,
        "m_unique": m_unique,
        "d_unique": d_unique,
        "constraint_violation_count": len(violations),
        "saturation_reason_count": sum(bool(row) for row in saturation_reasons),
        "performance_endpoints_inspected": False,
        "trace_sha256": trace_sha256,
    }
