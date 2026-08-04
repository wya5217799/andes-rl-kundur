"""Fail-closed classifier for the R324 model-fidelity gate.

The probe separates three questions in a fixed order: whether the execution is
admissible, whether every material value is honestly bound to a source or an
explicit assumption, and whether both adjacent TDS refinements meet the frozen
open-loop convergence tolerances.  Invalid executions never expose numerical
convergence as scientific evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

EXPECTED_SUBSTEPS = (5, 10, 20)
EXPECTED_TIME_SECONDS = 0.5 + 0.2 * np.arange(1, 26)
EXPECTED_PULSE = np.asarray([0.0, 0.0, -0.05, 0.05])

POWER_MAX_ABS = 5e-4
FREQUENCY_MAX_ABS_HZ = 1e-3
SOC_MAX_ABS = 1e-6
TERMINAL_NORMALIZED_L2 = 1e-4
PEAK_TIME_MAX_ABS_SECONDS = 0.2 + 1e-12

ALLOWED_PROVENANCE_CLASSES = {
    "case-source",
    "literature-derived",
    "official-model-default",
    "derived",
    "explicit-modelling-assumption",
}

REQUIRED_PARAMETER_IDS = frozenset(
    {
        "kundur_case_identity",
        "system_base_mva",
        "nominal_frequency_hz",
        "original_g4_retained",
        "default_line_trip_disabled",
        "controlled_vsg_locations",
        "controlled_vsg_device_rating_mva",
        "controlled_vsg_active_dispatch_device_pu",
        "controlled_vsg_inertia_device",
        "controlled_vsg_damping_device",
        "controlled_vsg_stator_resistance_pu",
        "controlled_vsg_transient_reactance_pu",
        "radial_line_voltage_kv",
        "radial_line_resistance_pu",
        "radial_line_reactance_pu",
        "radial_line_shunt_pu",
        "added_loads_system_pu",
        "wind_proxy_contract",
        "storage_locations",
        "storage_module_count",
        "storage_module_power_mva",
        "storage_module_energy_mwh",
        "storage_device_power_mva",
        "storage_device_energy_mwh",
        "storage_power_limit_device_pu",
        "storage_active_current_limit_device_pu",
        "storage_active_current_lag_seconds",
        "storage_soc_integrator_scale",
        "storage_soc_contract",
        "storage_efficiencies",
        "storage_active_power_priority",
        "storage_reactive_power_excluded",
        "external_ramp_system_pu_per_second",
        "control_period_seconds",
        "initialization_seconds",
        "tds_method",
        "tds_solver_tolerances",
        "tds_substep_refinement",
        "open_loop_pulse",
        "open_loop_active_duration_seconds",
        "open_loop_recovery_duration_seconds",
    }
)

_BINDING_FIELDS = {
    "id",
    "value",
    "unit",
    "base",
    "represented_object",
    "source_locator",
    "provenance_class",
    "binding_status",
    "physically_calibrated",
    "calibration_ceiling",
}


def _finite_array(value: object, shape: tuple[int, ...]) -> np.ndarray | None:
    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if array.shape != shape or not np.all(np.isfinite(array)):
        return None
    return array


def _trace_arrays(trace: Mapping[str, Any]) -> dict[str, np.ndarray] | None:
    time = _finite_array(trace.get("time_seconds"), (25,))
    power = _finite_array(trace.get("achieved_power_system_pu"), (25, 4))
    frequency = _finite_array(trace.get("frequency_hz"), (25, 4))
    soc = _finite_array(trace.get("soc"), (25, 4))
    requested = _finite_array(trace.get("requested_power_system_pu"), (25, 4))
    commanded = _finite_array(trace.get("commanded_power_system_pu"), (25, 4))
    external = _finite_array(trace.get("external_command_readback_system_pu"), (25, 4))
    m_system = _finite_array(trace.get("vsg_m_actual_system"), (25, 4))
    d_system = _finite_array(trace.get("vsg_d_actual_system"), (25, 4))
    dae_g = _finite_array(trace.get("dae_g_residual_max"), (25,))
    try:
        terminal_x = np.asarray(trace.get("terminal_x"), dtype=float)
        terminal_y = np.asarray(trace.get("terminal_y"), dtype=float)
    except (TypeError, ValueError):
        return None
    if (
        time is None
        or power is None
        or frequency is None
        or soc is None
        or requested is None
        or commanded is None
        or external is None
        or m_system is None
        or d_system is None
        or dae_g is None
        or terminal_x.ndim != 1
        or terminal_y.ndim != 1
        or terminal_x.size == 0
        or terminal_y.size == 0
        or not np.all(np.isfinite(terminal_x))
        or not np.all(np.isfinite(terminal_y))
    ):
        return None
    return {
        "time": time,
        "power": power,
        "frequency": frequency,
        "soc": soc,
        "requested": requested,
        "commanded": commanded,
        "external": external,
        "m_system": m_system,
        "d_system": d_system,
        "dae_g": dae_g,
        "terminal_x": terminal_x,
        "terminal_y": terminal_y,
    }


def _execution_valid(
    trace: Mapping[str, Any],
    arrays: Mapping[str, np.ndarray] | None,
) -> bool:
    if arrays is None:
        return False
    expected_request = np.zeros((25, 4))
    expected_request[:5] = EXPECTED_PULSE
    boolean_series = (
        "pflow_converged",
        "finite_state_algebraic",
        "line_8_in_service",
        "g4_in_service",
    )
    false_series = (
        "tds_failed",
        "external_saturation_active",
        "internal_limiter_active",
    )
    try:
        return bool(
            trace.get("completed") is True
            and trace.get("execution_guard_failures") == []
            and trace.get("tds_method") == "trapezoid"
            and trace.get("initialization_tolerance") == 1e-4
            and trace.get("initialization_tiny_correction_threshold") == 1e-10
            and trace.get("dynamic_tolerance") == 1e-10
            and trace.get("dynamic_tiny_correction_threshold") == 1e-16
            and np.allclose(
                arrays["requested"], expected_request, rtol=0.0, atol=1e-12
            )
            and np.allclose(
                arrays["commanded"], expected_request, rtol=0.0, atol=1e-12
            )
            and np.allclose(
                arrays["external"], expected_request, rtol=0.0, atol=1e-12
            )
            and np.allclose(arrays["m_system"], 400.0, rtol=0.0, atol=1e-10)
            and np.allclose(arrays["d_system"], 200.0, rtol=0.0, atol=1e-10)
            and np.max(arrays["dae_g"]) <= 1e-8
            and np.min(arrays["soc"]) >= 0.2
            and np.max(arrays["soc"]) <= 0.8
            and all(
                np.asarray(trace.get(name), dtype=bool).shape == (25,)
                and np.all(np.asarray(trace.get(name), dtype=bool))
                for name in boolean_series
            )
            and all(
                np.asarray(trace.get(name), dtype=bool).shape == (25,)
                and not np.any(np.asarray(trace.get(name), dtype=bool))
                for name in false_series
            )
            and np.asarray(trace.get("system_exit_code"), dtype=int).shape == (25,)
            and np.all(np.asarray(trace.get("system_exit_code"), dtype=int) == 0)
            and np.asarray(trace.get("md_write_count"), dtype=int).shape == (25,)
            and np.all(np.asarray(trace.get("md_write_count"), dtype=int) == 0)
            and np.asarray(trace.get("constraint_violation_count"), dtype=int).shape
            == (25,)
            and np.all(
                np.asarray(trace.get("constraint_violation_count"), dtype=int) == 0
            )
        )
    except (TypeError, ValueError):
        return False


def _parameter_inventory_valid(rows: object) -> bool:
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return False
    if not all(isinstance(row, Mapping) for row in rows):
        return False
    identifiers = [str(row.get("id")) for row in rows]
    return (
        len(identifiers) == len(REQUIRED_PARAMETER_IDS)
        and len(set(identifiers)) == len(identifiers)
        and set(identifiers) == REQUIRED_PARAMETER_IDS
        and all(_BINDING_FIELDS <= set(row) for row in rows)
    )


def _parameter_provenance(rows: Sequence[Mapping[str, Any]]) -> tuple[bool, list[str]]:
    unbound: list[str] = []
    for row in rows:
        identifier = str(row["id"])
        provenance_class = str(row["provenance_class"])
        source = str(row["source_locator"]).strip()
        ceiling = str(row["calibration_ceiling"]).strip()
        bound = (
            row["binding_status"] == "bound"
            and provenance_class in ALLOWED_PROVENANCE_CLASSES
            and bool(source)
            and bool(ceiling)
        )
        if provenance_class == "explicit-modelling-assumption":
            bound = bound and row["physically_calibrated"] is False
        if not bound:
            unbound.append(identifier)
    return not unbound, sorted(unbound)


def _peak_time(time: np.ndarray, signal: np.ndarray) -> float:
    magnitude = np.max(np.abs(signal), axis=1)
    return float(time[int(np.argmax(magnitude))])


def _terminal_error(coarse: np.ndarray, fine: np.ndarray) -> float:
    return float(np.linalg.norm(coarse - fine) / max(1.0, np.linalg.norm(fine)))


def _compare_adjacent(
    coarse_steps: int,
    coarse: Mapping[str, np.ndarray],
    fine_steps: int,
    fine: Mapping[str, np.ndarray],
) -> dict[str, Any]:
    power_error = float(np.max(np.abs(coarse["power"] - fine["power"])))
    frequency_error = float(
        np.max(np.abs(coarse["frequency"] - fine["frequency"]))
    )
    soc_error = float(np.max(np.abs(coarse["soc"] - fine["soc"])))
    terminal_x_error = _terminal_error(coarse["terminal_x"], fine["terminal_x"])
    terminal_y_error = _terminal_error(coarse["terminal_y"], fine["terminal_y"])
    power_peak_time_error = abs(
        _peak_time(coarse["time"], coarse["power"])
        - _peak_time(fine["time"], fine["power"])
    )
    frequency_peak_time_error = abs(
        _peak_time(coarse["time"], coarse["frequency"] - 60.0)
        - _peak_time(fine["time"], fine["frequency"] - 60.0)
    )
    gates = {
        "achieved_power": power_error <= POWER_MAX_ABS,
        "physical_frequency": frequency_error <= FREQUENCY_MAX_ABS_HZ,
        "soc": soc_error <= SOC_MAX_ABS,
        "terminal_x": terminal_x_error <= TERMINAL_NORMALIZED_L2,
        "terminal_y": terminal_y_error <= TERMINAL_NORMALIZED_L2,
        "power_peak_time": power_peak_time_error <= PEAK_TIME_MAX_ABS_SECONDS,
        "frequency_peak_time": (
            frequency_peak_time_error <= PEAK_TIME_MAX_ABS_SECONDS
        ),
    }
    return {
        "coarse_substeps": coarse_steps,
        "fine_substeps": fine_steps,
        "maximum_achieved_power_difference_system_pu": power_error,
        "maximum_frequency_difference_hz": frequency_error,
        "maximum_soc_difference": soc_error,
        "terminal_x_normalized_l2_difference": terminal_x_error,
        "terminal_y_normalized_l2_difference": terminal_y_error,
        "power_peak_time_difference_seconds": power_peak_time_error,
        "frequency_peak_time_difference_seconds": frequency_peak_time_error,
        "gates": gates,
        "pass": all(gates.values()),
    }


def evaluate_model_fidelity(payload: object) -> dict[str, Any]:
    """Return the registered R324 classification and bounded metrics."""

    if not isinstance(payload, Mapping):
        return {
            "classification": "INVALID-MODEL-FIDELITY-CHECK",
            "validity_guards": {"payload_mapping": False},
            "adjacent_comparisons": [],
            "gates": {},
        }

    rows = payload.get("parameter_bindings")
    traces = payload.get("traces")
    trace_list = (
        list(traces)
        if isinstance(traces, Sequence) and not isinstance(traces, (str, bytes))
        else []
    )
    trace_mappings = [trace for trace in trace_list if isinstance(trace, Mapping)]
    trace_by_steps = {
        int(trace.get("substeps", -1)): trace for trace in trace_mappings
    }
    arrays_by_steps = {
        steps: _trace_arrays(trace) for steps, trace in trace_by_steps.items()
    }

    validity_guards = {
        "identity": (
            payload.get("round") == "R324"
            and payload.get("question") == "Q-0079"
            and isinstance(payload.get("seal_sha256"), str)
            and len(str(payload.get("seal_sha256"))) == 64
        ),
        "parameter_inventory": _parameter_inventory_valid(rows),
        "trace_identity": (
            len(trace_mappings) == 3
            and set(trace_by_steps) == set(EXPECTED_SUBSTEPS)
            and all(
                trace.get("operating_point") == "OP0"
                and trace.get("coordinate") == "edge_2"
                and trace.get("sign") == "negative"
                and np.isclose(
                    float(trace.get("max_segment_seconds", float("nan"))),
                    0.2 / steps,
                    rtol=0.0,
                    atol=1e-15,
                )
                for steps, trace in trace_by_steps.items()
            )
        ),
        "trace_arrays_and_time_grid": (
            set(arrays_by_steps) == set(EXPECTED_SUBSTEPS)
            and all(value is not None for value in arrays_by_steps.values())
            and all(
                np.allclose(
                    value["time"], EXPECTED_TIME_SECONDS, rtol=0.0, atol=1e-9
                )
                for value in arrays_by_steps.values()
                if value is not None
            )
            and len(
                {
                    (
                        value["terminal_x"].shape,
                        value["terminal_y"].shape,
                    )
                    for value in arrays_by_steps.values()
                    if value is not None
                }
            )
            == 1
        ),
        "execution": (
            len(trace_mappings) == 3
            and all(
                _execution_valid(trace, arrays_by_steps.get(steps))
                for steps, trace in trace_by_steps.items()
            )
        ),
        "scope": (
            payload.get("physical_execution_performed") is True
            and payload.get("controller_executed") is False
            and payload.get("closed_loop_executed") is False
            and payload.get("eval_status")
            == "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE"
            and payload.get("distributed_agent_implementation_authorized") is False
            and payload.get("training_authorized") is False
        ),
    }
    if not all(validity_guards.values()):
        return {
            "classification": "INVALID-MODEL-FIDELITY-CHECK",
            "validity_guards": validity_guards,
            "adjacent_comparisons": [],
            "gates": {},
            "claim_ceiling": "invalid execution; no convergence metric admissible",
        }

    assert isinstance(rows, Sequence)
    binding_rows = [row for row in rows if isinstance(row, Mapping)]
    parameter_pass, unbound = _parameter_provenance(binding_rows)

    typed_arrays = {
        steps: value for steps, value in arrays_by_steps.items() if value is not None
    }
    comparisons = [
        _compare_adjacent(coarse, typed_arrays[coarse], fine, typed_arrays[fine])
        for coarse, fine in zip(EXPECTED_SUBSTEPS, EXPECTED_SUBSTEPS[1:])
    ]
    convergence_pass = all(item["pass"] for item in comparisons)

    if not parameter_pass:
        classification = "PARAMETER-PROVENANCE-NO-GO"
    elif not convergence_pass:
        classification = "TIME-STEP-CONVERGENCE-NO-GO"
    else:
        classification = "MODEL-FIDELITY-GATE-PASS"

    assumption_ids = sorted(
        str(row["id"])
        for row in binding_rows
        if row["provenance_class"] == "explicit-modelling-assumption"
    )
    return {
        "classification": classification,
        "validity_guards": validity_guards,
        "parameter_binding": {
            "row_count": len(binding_rows),
            "unbound_ids": unbound,
            "explicit_assumption_ids": assumption_ids,
            "physical_calibration_established": False,
        },
        "adjacent_comparisons": comparisons,
        "thresholds": {
            "maximum_achieved_power_difference_system_pu": POWER_MAX_ABS,
            "maximum_frequency_difference_hz": FREQUENCY_MAX_ABS_HZ,
            "maximum_soc_difference": SOC_MAX_ABS,
            "terminal_state_normalized_l2_difference": TERMINAL_NORMALIZED_L2,
            "maximum_peak_time_difference_seconds": PEAK_TIME_MAX_ABS_SECONDS,
        },
        "gates": {
            "parameter_provenance": parameter_pass,
            "all_adjacent_refinements": convergence_pass,
        },
        "claim_ceiling": (
            "one unchanged phasor-domain proxy has explicit parameter bindings "
            "and one finite open-loop control-boundary time-step convergence result; "
            "no physical calibration, controller efficacy, EMT, or learning claim"
        ),
    }
