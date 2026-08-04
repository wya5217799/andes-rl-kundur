"""Pure validity and decision seam for the R333 physical PQ bank.

The probe consumes only the sealed contract and structured execution payload.
It does not import ANDES, open simulator state, fit a model, shift traces, or
select thresholds after execution.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: object) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()


def _finite(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None


def _close(value: object, expected: float, tolerance: float) -> bool:
    number = _finite(value)
    return number is not None and abs(number - expected) <= tolerance


def _matrix(value: object, *, rows: int) -> np.ndarray | None:
    try:
        matrix = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None
    if matrix.shape != (rows, 4) or not np.all(np.isfinite(matrix)):
        return None
    return matrix


def _nested_matrix(
    payload: Mapping[str, Mapping[str, object]],
    point: str,
    sign: str,
    *,
    rows: int,
) -> np.ndarray | None:
    point_payload = payload.get(point)
    if not isinstance(point_payload, Mapping):
        return None
    return _matrix(point_payload.get(sign), rows=rows)


_CONSTANT_POWER_WEIGHTS = {
    "p2p": 1.0,
    "p2i": 0.0,
    "p2z": 0.0,
    "q2q": 1.0,
    "q2i": 0.0,
    "q2z": 0.0,
}


def _snapshot_valid(
    snapshot: object,
    *,
    device_idx: str,
    bus_idx: int,
    expected_p: float,
    expected_q: float,
    expected_time: float,
    tolerance: float,
) -> bool:
    row = _mapping(snapshot)
    replacements = _mapping(row.get("replacement_records"))
    fload = _sequence(replacements.get("FLoad"))
    zip_load = _sequence(replacements.get("ZIP"))
    no_active_replacement = all(
        not bool(_mapping(item).get("raw_active"))
        for item in (*fload, *zip_load)
    )
    return bool(
        row.get("device_idx") == device_idx
        and row.get("bus_idx") == bus_idx
        and row.get("raw_active") is True
        and row.get("effective_active") is True
        and row.get("active") is True
        and _close(row.get("Ppf_system_pu"), expected_p, tolerance)
        and _close(row.get("Qpf_system_pu"), expected_q, tolerance)
        and _close(row.get("dae_time_seconds"), expected_time, 1e-9)
        and row.get("pq2z_config") == 0
        and row.get("vcmp_enable") == 0
        and _mapping(row.get("constant_power_weights")) == _CONSTANT_POWER_WEIGHTS
        and row.get("active_fload_replacements_for_device") == 0
        and row.get("active_zip_replacements_for_device") == 0
        and no_active_replacement
    )


def _expected_inventory(
    *,
    device_idx: str,
    initial_p: float,
    initial_q: float,
    delta: float,
    apply_time: float,
    restore_time: float,
) -> list[dict[str, object]]:
    disturbed = initial_p + delta
    return [
        {
            "idx": "R333_apply_p",
            "model": "PQ",
            "dev": device_idx,
            "src": "Ppf",
            "t": apply_time,
            "method": "=",
            "amount": disturbed,
        },
        {
            "idx": "R333_apply_q",
            "model": "PQ",
            "dev": device_idx,
            "src": "Qpf",
            "t": apply_time,
            "method": "=",
            "amount": initial_q,
        },
        {
            "idx": "R333_restore_p",
            "model": "PQ",
            "dev": device_idx,
            "src": "Ppf",
            "t": restore_time,
            "method": "=",
            "amount": initial_p,
        },
        {
            "idx": "R333_restore_q",
            "model": "PQ",
            "dev": device_idx,
            "src": "Qpf",
            "t": restore_time,
            "method": "=",
            "amount": initial_q,
        },
    ]


def _event_receipts_valid(
    receipts: object,
    *,
    expected_inventory: Sequence[Mapping[str, object]],
    initial_p: float,
    initial_q: float,
    delta: float,
    apply_observation_time: float,
    restore_observation_time: float,
    tolerance: float,
) -> bool:
    rows = _sequence(receipts)
    if len(rows) != 4 or not all(isinstance(row, Mapping) for row in rows):
        return False
    disturbed = initial_p + delta
    expected_values = (
        (initial_p, disturbed, apply_observation_time),
        (initial_q, initial_q, apply_observation_time),
        (disturbed, initial_p, restore_observation_time),
        (initial_q, initial_q, restore_observation_time),
    )
    for row, event, (before, target, observation_time) in zip(
        rows,
        expected_inventory,
        expected_values,
        strict=True,
    ):
        parameter = str(event["src"])
        quantity = (
            "active-power consumption"
            if parameter == "Ppf"
            else "reactive-power consumption"
        )
        if not (
            row.get("idx") == event["idx"]
            and row.get("mechanism") == "Alter"
            and row.get("device_idx") == event["dev"]
            and row.get("parameter") == parameter
            and row.get("method") == "="
            and _close(row.get("scheduled_event_time_seconds"), float(event["t"]), tolerance)
            and _close(row.get("observation_time_seconds"), observation_time, 1e-9)
            and float(observation_time) >= float(event["t"])
            and _close(row.get("before_system_pu"), before, tolerance)
            and _close(row.get("target_system_pu"), target, tolerance)
            and _close(row.get("readback_system_pu"), target, tolerance)
            and _close(row.get("system_base_mva"), 100.0, tolerance)
            and row.get("quantity") == quantity
            and row.get("positive_sign") == "increased consumption"
            and row.get("exact_event_row_semantics") == "pre-event"
        ):
            return False
    return True


def _event_grid_valid(times: object, *, apply_time: float, restore_time: float) -> bool:
    try:
        grid = np.asarray(times, dtype=float).reshape(-1)
    except (TypeError, ValueError):
        return False
    if grid.size == 0 or not np.all(np.isfinite(grid)) or not np.all(np.diff(grid) > 0.0):
        return False
    for event_time in (apply_time, restore_time):
        before = np.flatnonzero(np.isclose(grid, event_time - 1e-4, rtol=0.0, atol=1e-12))
        exact = np.flatnonzero(grid == event_time)
        after = np.flatnonzero(np.isclose(grid, event_time + 1e-4, rtol=0.0, atol=1e-12))
        if not (
            len(before) == len(exact) == len(after) == 1
            and before[0] < exact[0] < after[0]
        ):
            return False
    return True


def _callback_audit_valid(
    row: Mapping[str, Any],
    *,
    apply_time: float,
    restore_time: float,
) -> bool:
    batches = _sequence(row.get("event_callback_audit"))
    counts = _mapping(row.get("event_fire_counts"))
    expected = (
        (
            apply_time,
            ["R333_apply_p", "R333_apply_q"],
            "pre_event_snapshot",
            "post_apply_snapshot",
        ),
        (
            restore_time,
            ["R333_restore_p", "R333_restore_q"],
            "pre_restore_snapshot",
            "post_restore_snapshot",
        ),
    )
    event_ids = (*expected[0][1], *expected[1][1])
    if len(batches) != 2 or any(counts.get(name) != 1 for name in event_ids):
        return False
    for batch, (event_time, ids, before_name, after_name) in zip(
        batches,
        expected,
        strict=True,
    ):
        audit = _mapping(batch)
        if not (
            _close(audit.get("dae_time_seconds"), event_time, 1e-12)
            and audit.get("event_ids") == ids
            and audit.get("callback_action") is True
            and _mapping(audit.get("before")) == _mapping(row.get(before_name))
            and _mapping(audit.get("after")) == _mapping(row.get(after_name))
        ):
            return False
    return True


def _configuration_trace_valid(
    row: Mapping[str, Any],
    *,
    expected_point: Mapping[str, Any],
    nominal_tie_lines: Mapping[str, Any],
    steps: int,
    actuator_limit: float,
) -> bool:
    expected_configuration = {
        "name": expected_point.get("name"),
        "vsg_m_device": expected_point.get("vsg_m_device"),
        "vsg_d_device": expected_point.get("vsg_d_device"),
        "tie_rx_scale": expected_point.get("tie_rx_scale"),
        "initial_soc": expected_point.get("initial_soc"),
    }
    if _mapping(row.get("operating_point_configuration")) != expected_configuration:
        return False
    tie_readback = _mapping(row.get("tie_line_readback"))
    if set(tie_readback) != set(nominal_tie_lines):
        return False
    scale = float(expected_point["tie_rx_scale"])
    for line_idx, nominal in nominal_tie_lines.items():
        actual = _mapping(tie_readback.get(line_idx))
        reference = _mapping(nominal)
        if not (
            _close(actual.get("r"), scale * float(reference["r"]), 1e-12)
            and _close(actual.get("x"), scale * float(reference["x"]), 1e-12)
        ):
            return False
    traces = _sequence(row.get("traces"))
    if len(traces) != steps or not all(isinstance(trace, Mapping) for trace in traces):
        return False
    expected_m = 2.0 * float(expected_point["vsg_m_device"])
    expected_d = 2.0 * float(expected_point["vsg_d_device"])
    expected_soc = float(expected_point["initial_soc"])
    for trace in traces:
        try:
            m_values = np.asarray(trace.get("vsg_m_actual_system"), dtype=float)
            d_values = np.asarray(trace.get("vsg_d_actual_system"), dtype=float)
            soc = np.asarray(trace.get("bess_soc"), dtype=float)
        except (TypeError, ValueError):
            return False
        internal = _mapping(trace.get("bess_internal"))
        if not (
            m_values.shape == d_values.shape == soc.shape == (4,)
            and np.allclose(m_values, expected_m, rtol=0.0, atol=1e-12)
            and np.allclose(d_values, expected_d, rtol=0.0, atol=1e-12)
            and np.allclose(soc, expected_soc, rtol=0.0, atol=1e-12)
        ):
            return False
        for name in ("Pext0", "Pext", "Pref", "Psum"):
            try:
                values = np.asarray(internal.get(name), dtype=float)
            except (TypeError, ValueError):
                return False
            if values.shape != (4,) or np.max(np.abs(values)) > actuator_limit:
                return False
    return True


def _record_execution_valid(
    row: Mapping[str, Any],
    *,
    steps: int,
    residual_limit: float,
) -> bool:
    times = np.asarray(_sequence(row.get("time_seconds")), dtype=float)
    time_valid = bool(
        times.shape == (steps,)
        and np.all(np.isfinite(times))
        and np.allclose(times, 0.7 + 0.2 * np.arange(steps), rtol=0.0, atol=1e-9)
    )
    residual = _finite(row.get("algebraic_residual_absolute_maximum"))
    return bool(
        row.get("completed") is True
        and row.get("tds_failed") is False
        and row.get("n_steps") == steps
        and row.get("requested_steps") == steps
        and row.get("all_states_finite") is True
        and row.get("system_exit_code_maximum") == 0
        and residual is not None
        and residual <= residual_limit
        and row.get("tds_grid_guard") is True
        and time_valid
    )


def _zero_actuator_valid(row: Mapping[str, Any], *, limit: float) -> bool:
    powers = (
        _finite(row.get("bess_requested_power_absolute_maximum_system_pu")),
        _finite(row.get("bess_commanded_power_absolute_maximum_system_pu")),
        _finite(row.get("bess_actual_power_absolute_maximum_system_pu")),
        _finite(row.get("bess_internal_power_absolute_maximum_system_pu")),
    )
    return bool(
        row.get("md_write_count_maximum") == 0
        and all(value is not None and value <= limit for value in powers)
        and row.get("internal_limiter_active") is False
        and row.get("external_saturation_active") is False
        and row.get("constraint_violation_count") == 0
    )


def _response_metrics(
    physical: np.ndarray,
    predicted: np.ndarray,
    baseline: np.ndarray,
    *,
    delta: float,
) -> dict[str, float | bool]:
    response = physical - baseline
    drift = baseline - baseline[0]
    signal_energy = float(np.sum(np.square(response)))
    drift_energy = float(np.sum(np.square(drift)))
    signal_ratio = signal_energy / max(drift_energy, 1.0e-30)
    error = predicted - response
    nrmse = float(np.linalg.norm(error) / max(np.linalg.norm(response), 1.0e-30))
    response_peak = float(np.max(np.linalg.norm(response, axis=1)))
    peak_residual = float(
        np.max(np.linalg.norm(error, axis=1)) / max(response_peak, 1.0e-30)
    )
    common = response[:, 0]
    peak_index = int(np.argmax(np.abs(common)))
    sign_correct = bool(common[peak_index] * delta < 0.0)
    return {
        "signal_energy": signal_energy,
        "baseline_drift_energy": drift_energy,
        "signal_to_baseline_drift_energy_ratio": signal_ratio,
        "common_frequency_peak_sign_correct": sign_correct,
        "reduced_physical_total_nrmse": nrmse,
        "reduced_physical_peak_vector_residual": peak_residual,
    }


def analyse_pq_disturbance_identification(
    execution: object,
    contract: object,
    *,
    expected_seal_sha256: str,
    expected_dynamic_model_sha256: str,
    expected_coordinate_inputs: Mapping[str, Mapping[str, object]],
    expected_predictions: Mapping[str, Mapping[str, object]],
    evidence_chain_valid: bool,
) -> dict[str, object]:
    """Classify the exact R333 six-record signed PQ bank."""

    run = _mapping(execution)
    sealed = _mapping(contract)
    thresholds = _mapping(sealed.get("thresholds"))
    points = tuple(str(value) for value in _sequence(sealed.get("operating_points")))
    point_rows = _sequence(sealed.get("operating_point_records"))
    point_contracts = {
        str(row.get("name")): row for row in point_rows if isinstance(row, Mapping)
    }
    nominal_tie_lines = _mapping(sealed.get("nominal_tie_lines"))
    signs = tuple(str(value) for value in _sequence(sealed.get("signs")))
    device_idx = str(sealed.get("device_idx", ""))
    bus_idx = int(sealed.get("bus_idx", -1)) if _finite(sealed.get("bus_idx")) is not None else -1
    steps = int(sealed.get("steps", 0)) if _finite(sealed.get("steps")) is not None else 0
    active_steps = int(sealed.get("active_steps", 0)) if _finite(sealed.get("active_steps")) is not None else 0
    amplitude = _finite(sealed.get("amplitude_system_pu"))
    pre_event = _finite(sealed.get("pre_event_active_load_system_pu"))
    pre_event_q = _finite(sealed.get("pre_event_reactive_load_system_pu"))
    event_times = _mapping(sealed.get("event_times_seconds"))
    apply_time = _finite(event_times.get("apply"))
    restore_time = _finite(event_times.get("restore"))
    pq_tolerance = _finite(
        thresholds.get("pq_readback_absolute_tolerance_system_pu")
    )
    actuator_limit = _finite(
        thresholds.get("zero_actuator_power_absolute_maximum_system_pu")
    )
    residual_limit = _finite(
        thresholds.get("algebraic_residual_absolute_maximum")
    )
    signal_minimum = _finite(
        thresholds.get("signal_to_baseline_drift_energy_ratio_minimum")
    )
    nonlinearity_maximum = _finite(
        thresholds.get("pair_midpoint_nonlinearity_ratio_maximum")
    )
    nrmse_maximum = _finite(
        thresholds.get("reduced_physical_total_nrmse_maximum")
    )
    peak_maximum = _finite(
        thresholds.get("reduced_physical_peak_vector_residual_maximum")
    )
    contract_valid = bool(
        points == ("HS0", "HS1")
        and len(point_rows) == 2
        and set(point_contracts) == set(points)
        and nominal_tie_lines
        == {
            "Line_4": {"r": 0.02201, "x": 0.22001},
            "Line_5": {"r": 0.02202, "x": 0.22002},
            "Line_6": {"r": 0.022, "x": 0.22},
        }
        and signs == ("zero", "positive", "negative")
        and device_idx == "PQ_Bus14"
        and bus_idx == 14
        and tuple(_sequence(sealed.get("controlled_bus_order"))) == (12, 16, 14, 15)
        and tuple(_sequence(sealed.get("node_disturbance_map")))
        == (0.0, 0.0, -1.0, 0.0)
        and steps == 25
        and active_steps == 5
        and sealed.get("recovery_steps") == 20
        and _close(sealed.get("control_period_seconds"), 0.2, 1e-15)
        and sealed.get("physical_execution_planned") is True
        and sealed.get("physical_execution_performed") is False
        and amplitude is not None
        and amplitude > 0.0
        and pre_event is not None
        and pre_event > amplitude
        and pre_event_q is not None
        and apply_time == 0.5
        and restore_time == 1.5
        and all(
            value is not None and value >= 0.0
            for value in (
                pq_tolerance,
                actuator_limit,
                residual_limit,
                signal_minimum,
                nonlinearity_maximum,
                nrmse_maximum,
                peak_maximum,
            )
        )
    )

    raw_records = _sequence(run.get("records"))
    records = [row for row in raw_records if isinstance(row, Mapping)]
    expected_inventory = {(point, sign) for point in points for sign in signs}
    actual_inventory = [
        (str(row.get("operating_point")), str(row.get("sign"))) for row in records
    ]
    record_inventory = bool(
        len(raw_records) == len(expected_inventory)
        and len(records) == len(raw_records)
        and len(actual_inventory) == len(set(actual_inventory))
        and set(actual_inventory) == expected_inventory
    )
    by_key = {
        (str(row.get("operating_point")), str(row.get("sign"))): row
        for row in records
    }

    identity = bool(
        run.get("round") == sealed.get("round") == "R333"
        and run.get("question") == sealed.get("question") == "Q-0085"
        and run.get("seal_sha256") == expected_seal_sha256
        and run.get("dynamic_model_sha256") == expected_dynamic_model_sha256
        and evidence_chain_valid is True
        and run.get("source_identity") is True
        and run.get("parent_identity") is True
        and run.get("runtime_identity") is True
        and run.get("physical_execution_performed") is True
    )
    scope_exclusions = bool(
        run.get("controller_executed") is False
        and run.get("closed_loop_executed") is False
        and run.get("distributed_runtime_executed") is False
        and run.get("training_executed") is False
        and run.get("eval_executed") is False
    )

    pq_write_and_restoration = contract_valid and record_inventory
    pq_effective_and_event_timing = contract_valid and record_inventory
    numerical_execution = contract_valid and record_inventory
    zero_actuator = contract_valid and record_inventory
    topology_and_boundaries = contract_valid and record_inventory
    output_payload = contract_valid and record_inventory
    model_and_input_binding = contract_valid and record_inventory
    operating_point_binding = contract_valid and record_inventory
    matrices: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
    if contract_valid and record_inventory:
        assert amplitude is not None
        assert pre_event is not None
        assert pre_event_q is not None
        assert apply_time is not None
        assert restore_time is not None
        assert pq_tolerance is not None
        assert actuator_limit is not None
        assert residual_limit is not None
        for point in points:
            for sign in signs:
                row = by_key[(point, sign)]
                expected_delta = {
                    "zero": 0.0,
                    "positive": amplitude,
                    "negative": -amplitude,
                }[sign]
                pq_write_and_restoration = bool(
                    pq_write_and_restoration
                    and row.get("device_idx") == device_idx
                    and _close(
                        row.get("delta_load_system_pu"),
                        expected_delta,
                        pq_tolerance,
                    )
                )
                disturbed = pre_event + expected_delta
                times = np.asarray(_sequence(row.get("time_seconds")), dtype=float)
                terminal_time = (
                    float(times[-1]) if times.shape == (steps,) else float("nan")
                )
                expected_events = _expected_inventory(
                    device_idx=device_idx,
                    initial_p=pre_event,
                    initial_q=pre_event_q,
                    delta=expected_delta,
                    apply_time=apply_time,
                    restore_time=restore_time,
                )
                pq_write_and_restoration = bool(
                    pq_write_and_restoration
                    and _snapshot_valid(
                        row.get("pre_event_snapshot"),
                        device_idx=device_idx,
                        bus_idx=bus_idx,
                        expected_p=pre_event,
                        expected_q=pre_event_q,
                        expected_time=apply_time,
                        tolerance=pq_tolerance,
                    )
                    and _snapshot_valid(
                        row.get("post_apply_snapshot"),
                        device_idx=device_idx,
                        bus_idx=bus_idx,
                        expected_p=disturbed,
                        expected_q=pre_event_q,
                        expected_time=apply_time,
                        tolerance=pq_tolerance,
                    )
                    and _snapshot_valid(
                        row.get("pre_restore_snapshot"),
                        device_idx=device_idx,
                        bus_idx=bus_idx,
                        expected_p=disturbed,
                        expected_q=pre_event_q,
                        expected_time=restore_time,
                        tolerance=pq_tolerance,
                    )
                    and _snapshot_valid(
                        row.get("post_restore_snapshot"),
                        device_idx=device_idx,
                        bus_idx=bus_idx,
                        expected_p=pre_event,
                        expected_q=pre_event_q,
                        expected_time=restore_time,
                        tolerance=pq_tolerance,
                    )
                    and _snapshot_valid(
                        row.get("terminal_snapshot"),
                        device_idx=device_idx,
                        bus_idx=bus_idx,
                        expected_p=pre_event,
                        expected_q=pre_event_q,
                        expected_time=terminal_time,
                        tolerance=pq_tolerance,
                    )
                    and _event_receipts_valid(
                        row.get("event_receipts"),
                        expected_inventory=expected_events,
                        initial_p=pre_event,
                        initial_q=pre_event_q,
                        delta=expected_delta,
                        apply_observation_time=apply_time,
                        restore_observation_time=restore_time,
                        tolerance=pq_tolerance,
                    )
                )
                weights = _mapping(row.get("constant_power_weights"))
                pq_effective_and_event_timing = bool(
                    pq_effective_and_event_timing
                    and row.get("pq_active") is True
                    and weights == _CONSTANT_POWER_WEIGHTS
                    and row.get("active_fload_replacements_for_device") == 0
                    and row.get("active_zip_replacements_for_device") == 0
                    and row.get("event_inventory") == expected_events
                    and row.get("alter_event_inventory_guard") is True
                    and row.get("exact_event_sample_order_guard") is True
                    and _callback_audit_valid(
                        row,
                        apply_time=apply_time,
                        restore_time=restore_time,
                    )
                    and _event_grid_valid(
                        row.get("tds_time_grid_seconds"),
                        apply_time=apply_time,
                        restore_time=restore_time,
                    )
                )
                numerical_execution = bool(
                    numerical_execution
                    and _record_execution_valid(
                        row,
                        steps=steps,
                        residual_limit=residual_limit,
                    )
                )
                zero_actuator = bool(
                    zero_actuator
                    and _zero_actuator_valid(row, limit=actuator_limit)
                )
                operating_point_binding = bool(
                    operating_point_binding
                    and _configuration_trace_valid(
                        row,
                        expected_point=point_contracts[point],
                        nominal_tie_lines=nominal_tie_lines,
                        steps=steps,
                        actuator_limit=actuator_limit,
                    )
                )
                topology_and_boundaries = bool(
                    topology_and_boundaries
                    and row.get("line_8_all_in_service") is True
                    and row.get("g4_all_in_service") is True
                    and row.get("negative_load_crossing") is False
                )
                physical = _matrix(row.get("output_coordinates"), rows=steps)
                recorded_prediction = _matrix(
                    row.get("predicted_output_coordinates"),
                    rows=steps,
                )
                expected_input = _nested_matrix(
                    expected_coordinate_inputs,
                    point,
                    sign,
                    rows=steps,
                )
                recorded_input = _matrix(
                    row.get("coordinate_input_sequence"),
                    rows=steps,
                )
                expected_prediction = _nested_matrix(
                    expected_predictions,
                    point,
                    sign,
                    rows=steps,
                )
                model_and_input_binding = bool(
                    model_and_input_binding
                    and row.get("seal_sha256") == expected_seal_sha256
                    and row.get("dynamic_model_sha256")
                    == expected_dynamic_model_sha256
                    and recorded_input is not None
                    and expected_input is not None
                    and np.allclose(
                        recorded_input,
                        expected_input,
                        rtol=0.0,
                        atol=1e-15,
                    )
                    and recorded_prediction is not None
                    and expected_prediction is not None
                    and np.allclose(
                        recorded_prediction,
                        expected_prediction,
                        rtol=0.0,
                        atol=1e-15,
                    )
                )
                if physical is None or expected_prediction is None:
                    output_payload = False
                else:
                    matrices[(point, sign)] = (physical, expected_prediction)

    validity_guards: dict[str, bool] = {
        "contract": contract_valid,
        "identity": identity,
        "record_inventory": record_inventory,
        "pq_write_and_restoration": pq_write_and_restoration,
        "pq_effective_and_event_timing": pq_effective_and_event_timing,
        "numerical_execution": numerical_execution,
        "zero_actuator": zero_actuator,
        "topology_and_boundaries": topology_and_boundaries,
        "operating_point_binding": operating_point_binding,
        "model_and_input_binding": model_and_input_binding,
        "output_payload": output_payload,
        "scope_exclusions": scope_exclusions,
    }
    validity_guards["all"] = all(validity_guards.values())

    record_metrics: list[dict[str, object]] = []
    point_metrics: list[dict[str, object]] = []
    physical_channel_observable = validity_guards["all"]
    load_sign_correct = validity_guards["all"]
    paired_local_linearity = validity_guards["all"]
    frozen_channel_equivalence = validity_guards["all"]
    if validity_guards["all"]:
        assert signal_minimum is not None
        assert nonlinearity_maximum is not None
        assert nrmse_maximum is not None
        assert peak_maximum is not None
        assert amplitude is not None
        for point in points:
            baseline = matrices[(point, "zero")][0]
            responses: dict[str, np.ndarray] = {}
            for sign, delta in (("positive", amplitude), ("negative", -amplitude)):
                physical, predicted = matrices[(point, sign)]
                metrics = _response_metrics(
                    physical,
                    predicted,
                    baseline,
                    delta=delta,
                )
                record_metrics.append(
                    {"operating_point": point, "sign": sign, **metrics}
                )
                responses[sign] = physical - baseline
                physical_channel_observable = bool(
                    physical_channel_observable
                    and metrics["signal_to_baseline_drift_energy_ratio"]
                    >= signal_minimum
                )
                load_sign_correct = bool(
                    load_sign_correct
                    and metrics["common_frequency_peak_sign_correct"] is True
                )
                frozen_channel_equivalence = bool(
                    frozen_channel_equivalence
                    and metrics["reduced_physical_total_nrmse"] <= nrmse_maximum
                    and metrics["reduced_physical_peak_vector_residual"]
                    <= peak_maximum
                )
            midpoint = 0.5 * (responses["positive"] + responses["negative"])
            signed_scale = 0.5 * (
                np.linalg.norm(responses["positive"])
                + np.linalg.norm(responses["negative"])
            )
            nonlinearity = float(
                np.linalg.norm(midpoint) / max(float(signed_scale), 1.0e-30)
            )
            point_metrics.append(
                {
                    "operating_point": point,
                    "pair_midpoint_nonlinearity_ratio": nonlinearity,
                }
            )
            paired_local_linearity = bool(
                paired_local_linearity and nonlinearity <= nonlinearity_maximum
            )

    if not validity_guards["all"]:
        classification = "INVALID-PHYSICAL-DISTURBANCE-IDENTIFICATION"
        identification_guards: dict[str, bool | None] = {
            "physical_channel_observable": None,
            "load_sign_correct": None,
            "paired_local_linearity": None,
            "frozen_channel_equivalence": None,
            "all": None,
        }
        record_metrics = []
        point_metrics = []
    else:
        identification_guards = {
            "physical_channel_observable": physical_channel_observable,
            "load_sign_correct": load_sign_correct,
            "paired_local_linearity": paired_local_linearity,
            "frozen_channel_equivalence": frozen_channel_equivalence,
        }
        identification_guards["all"] = all(identification_guards.values())
        if not identification_guards["all"]:
            classification = "BLOCK"
        else:
            classification = "QUALIFY"

    return {
        "classification": classification,
        "validity_guards": validity_guards,
        "identification_guards": identification_guards,
        "record_metrics": record_metrics,
        "point_metrics": point_metrics,
        "invalid_reasons": [
            name
            for name, passed in validity_guards.items()
            if name != "all" and not passed
        ],
        "blocking_reasons": [
            name
            for name, passed in identification_guards.items()
            if name != "all" and passed is False
        ],
        "scope": {
            "identified_physical_channel_count": (
                1 if classification == "QUALIFY" else 0
            ),
            "identified_device": device_idx,
            "successor_package_required": True,
            "controller_authorized": False,
            "distributed_agent_authorized": False,
            "training_authorized": False,
            "eval_executed": False,
            "claim_ceiling": (
                "one Bus14 active-load channel, one amplitude and waveform, "
                "two operating points, phasor-domain electromechanical only"
            ),
        },
    }
