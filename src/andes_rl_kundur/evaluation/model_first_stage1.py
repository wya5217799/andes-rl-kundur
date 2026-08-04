"""Pure Stage-1 authority and coupling diagnostics for the model-first plant.

This module has no ANDES import.  It evaluates source-hashed trace records but
does not authorize training or replace the round/feed/claim verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    Stage1OperatingPoint,
    stage1_operating_points,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)

ACTIVE_STEPS = 5
TOTAL_STEPS = 25
TIME_STEP_SECONDS = 0.2
POWER_MATCH_TOLERANCE = 1e-12
POWER_ZERO_TOLERANCE = 1e-8
MD_TOLERANCE = 1e-10
ALGEBRAIC_RESIDUAL_MAX = 1e-8
SIGNAL_TO_DRIFT_MIN = 20.0
OP0_NONLINEARITY_MAX = 0.25
ALL_POINT_NONLINEARITY_MAX = 0.50


def _finite_matrix(values: object, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 2 or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite matrix")
    return array


def paired_response_metrics(
    zero: object,
    positive: object,
    negative: object,
    *,
    input_trace: object,
    input_kind: Literal["common", "edge"],
) -> dict[str, float]:
    """Measure symmetric signal, midpoint error, and cross/self L2 gains.

    Coordinate column zero is common and the remaining columns are the exact
    differential complement.  ``input_kind`` controls which output block is
    counted as self versus cross response.
    """

    baseline = _finite_matrix(zero, name="zero")
    plus = _finite_matrix(positive, name="positive")
    minus = _finite_matrix(negative, name="negative")
    command = _finite_matrix(input_trace, name="input_trace")
    if plus.shape != baseline.shape or minus.shape != baseline.shape:
        raise ValueError("paired response matrices must have identical shapes")
    if baseline.shape[1] < 2:
        raise ValueError("response must contain common and differential coordinates")
    if command.shape[0] != baseline.shape[0]:
        raise ValueError("input and response time dimensions must match")
    if input_kind not in {"common", "edge"}:
        raise ValueError("input_kind must be common or edge")

    plus_delta = plus - baseline
    minus_delta = minus - baseline
    paired_signal = 0.5 * (plus - minus)
    midpoint_error = 0.5 * (plus + minus) - baseline
    response_scale = 0.5 * (
        float(np.linalg.norm(plus_delta)) + float(np.linalg.norm(minus_delta))
    )
    baseline_drift = baseline - baseline[[0], :]
    input_norm = max(float(np.linalg.norm(command)), 1e-15)
    common_norm = float(np.linalg.norm(paired_signal[:, 0]))
    differential_norm = float(np.linalg.norm(paired_signal[:, 1:]))
    if input_kind == "common":
        self_norm, cross_norm = common_norm, differential_norm
    else:
        self_norm, cross_norm = differential_norm, common_norm
    return {
        "signal_l2": float(np.linalg.norm(paired_signal)),
        "baseline_drift_l2": float(np.linalg.norm(baseline_drift)),
        "signal_to_baseline_drift_ratio": float(np.linalg.norm(paired_signal))
        / max(float(np.linalg.norm(baseline_drift)), 1e-15),
        "midpoint_nonlinearity_ratio": float(np.linalg.norm(midpoint_error))
        / max(response_scale, 1e-15),
        "self_gain": self_norm / input_norm,
        "cross_gain": cross_norm / input_norm,
    }


def _vector(row: Mapping[str, object], key: str) -> np.ndarray:
    value = np.asarray(row[key], dtype=float)
    if value.shape != (4,) or not np.all(np.isfinite(value)):
        raise ValueError(f"{key} must be a finite four-vector")
    return value


def _trace_rows(record: Mapping[str, object]) -> list[Mapping[str, object]]:
    rows = record.get("traces")
    if not isinstance(rows, list) or len(rows) != TOTAL_STEPS:
        raise ValueError("trace must contain exactly 25 rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("every trace row must be an object")
    return rows


def _expected_request(
    record: Mapping[str, object],
    *,
    step: int,
) -> np.ndarray:
    coordinate = str(record["coordinate"])
    sign = str(record["sign"])
    if coordinate == "zero":
        return np.zeros(4)
    vectors = stage1_power_coordinates()
    if coordinate not in vectors or sign not in {"positive", "negative"}:
        raise ValueError("unknown Stage-1 coordinate/sign")
    if step >= ACTIVE_STEPS:
        return np.zeros(4)
    return vectors[coordinate] * (1.0 if sign == "positive" else -1.0)


def _record_execution_valid(
    record: Mapping[str, object],
    *,
    expected_round: str,
    expected_question: str,
) -> bool:
    try:
        rows = _trace_rows(record)
        if (
            record.get("round") != expected_round
            or record.get("question") != expected_question
            or not record.get("seal_sha256")
            or record.get("completed") is not True
            or record.get("tds_failed") is not False
            or int(record.get("n_steps", -1)) != TOTAL_STEPS
            or int(record.get("requested_steps", -1)) != TOTAL_STEPS
        ):
            return False
        time = np.asarray([row["t"] for row in rows], dtype=float)
        if not np.all(np.isfinite(time)) or not np.allclose(
            np.diff(time), TIME_STEP_SECONDS, rtol=0.0, atol=1e-9
        ):
            return False
        for row in rows:
            delta_f = _vector(row, "delta_f_physical_hz")
            frequency = _vector(row, "freq_hz_physical")
            if not np.allclose(frequency - 60.0, delta_f, rtol=0.0, atol=1e-9):
                return False
            if (
                row.get("pflow_converged") is not True
                or row.get("tds_failed") is not False
                or int(row.get("system_exit_code", -1)) != 0
                or row.get("finite_state_algebraic") is not True
                or float(row.get("dae_g_residual_max", np.inf))
                > ALGEBRAIC_RESIDUAL_MAX
                or row.get("line_8_in_service") is not True
                or row.get("g4_in_service") is not True
                or float(row.get("g4_m_actual_system", 0.0)) <= 0.1
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _two_phase_solver_valid(record: Mapping[str, object]) -> bool:
    try:
        initialization = record["initialization_solver"]
        structural = record["structural"]
        if not isinstance(initialization, Mapping) or not isinstance(
            structural, Mapping
        ):
            return False
        structural_initialization = structural["initialization_solver"]
        solver = structural["solver"]
        if not isinstance(structural_initialization, Mapping) or not isinstance(
            solver, Mapping
        ):
            return False
        if dict(structural_initialization) != dict(initialization):
            return False
        initialization_valid = (
            initialization.get("method") == "trapezoid"
            and float(initialization.get("convergence_tolerance", np.inf)) == 1e-4
            and float(initialization.get("tiny_correction_threshold", np.inf))
            == 1e-10
            and initialization.get("tds_test_ok") is True
            and int(initialization.get("system_exit_code", -1)) == 0
            and abs(float(initialization.get("endpoint_seconds", np.inf)) - 0.5)
            <= 1e-9
        )
        dynamic_valid = (
            solver.get("method") == "trapezoid"
            and float(solver.get("convergence_tolerance", np.inf)) == 1e-10
            and float(solver.get("tiny_correction_threshold", np.inf)) == 1e-16
            and int(solver.get("transition_count", -1)) == 1
            and solver.get("stopping_semantics")
            == "max_abs_newton_correction"
            and solver.get("readback_semantics")
            == "post_control_step_recomputed_dae_g"
        )
        row_valid = all(
            float(row.get("tds_convergence_tolerance", np.inf)) == 1e-10
            and float(row.get("tds_tiny_correction_threshold", np.inf)) == 1e-16
            and int(row.get("tds_solver_transition_count", -1)) == 1
            for row in _trace_rows(record)
        )
        return initialization_valid and dynamic_valid and row_valid
    except (KeyError, TypeError, ValueError):
        return False


def _power_layers_valid(record: Mapping[str, object]) -> bool:
    try:
        for step, row in enumerate(_trace_rows(record)):
            expected = _expected_request(record, step=step)
            for key in (
                "bess_requested_power_system_pu",
                "bess_commanded_power_system_pu",
                "bess_external_command_readback_system_pu",
                "bess_internal_power_reference_system_pu",
            ):
                if not np.allclose(
                    _vector(row, key), expected, rtol=0.0, atol=POWER_MATCH_TOLERANCE
                ):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _md_readback_valid(
    record: Mapping[str, object],
    point: Stage1OperatingPoint,
) -> bool:
    try:
        expected_m = np.full(4, point.vsg_m_system)
        expected_d = np.full(4, point.vsg_d_system)
        return all(
            int(row.get("md_write_count", -1)) == 0
            and np.allclose(
                _vector(row, "vsg_m_actual_system"),
                expected_m,
                rtol=0.0,
                atol=MD_TOLERANCE,
            )
            and np.allclose(
                _vector(row, "vsg_d_actual_system"),
                expected_d,
                rtol=0.0,
                atol=MD_TOLERANCE,
            )
            for row in _trace_rows(record)
        )
    except (KeyError, TypeError, ValueError):
        return False


def _achieved_power_valid(record: Mapping[str, object]) -> bool:
    try:
        rows = _trace_rows(record)
        expected = _expected_request(record, step=ACTIVE_STEPS - 1)
        actual = _vector(rows[ACTIVE_STEPS - 1], "bess_actual_power_system_pu")
        active = np.abs(expected) > POWER_ZERO_TOLERANCE
        if np.any(active):
            if np.any(actual[active] * expected[active] <= 0.0):
                return False
            if np.any(
                np.abs(actual[active] - expected[active])
                > 0.05 * np.abs(expected[active])
            ):
                return False
        if np.any(np.abs(actual[~active]) > POWER_ZERO_TOLERANCE):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _edge_neutrality_valid(record: Mapping[str, object]) -> bool:
    if not str(record.get("coordinate", "")).startswith("edge_"):
        return True
    try:
        rows = _trace_rows(record)
        for row in rows:
            for key in (
                "bess_requested_power_system_pu",
                "bess_commanded_power_system_pu",
            ):
                if abs(float(np.sum(_vector(row, key)))) > POWER_MATCH_TOLERANCE:
                    return False
        final = _vector(rows[ACTIVE_STEPS - 1], "bess_actual_power_system_pu")
        command = _vector(
            rows[ACTIVE_STEPS - 1], "bess_commanded_power_system_pu"
        )
        return abs(float(np.sum(final))) <= 0.05 * float(np.sum(np.abs(command)))
    except (KeyError, TypeError, ValueError):
        return False


def _soc_valid(record: Mapping[str, object]) -> bool:
    try:
        rows = _trace_rows(record)
        soc = np.asarray([_vector(row, "bess_soc") for row in rows])
        if np.min(soc) < 0.2 or np.max(soc) > 0.8:
            return False
        actual = np.asarray(
            [_vector(row, "bess_actual_power_system_pu") for row in rows]
        )
        energy_sign = np.sum(actual, axis=0)
        delta_soc = soc[-1] - float(record["initial_soc"])
        positive = energy_sign > POWER_ZERO_TOLERANCE
        negative = energy_sign < -POWER_ZERO_TOLERANCE
        if np.any(delta_soc[positive] >= 0.0) or np.any(delta_soc[negative] <= 0.0):
            return False
        if not np.any(positive | negative) and np.max(np.abs(delta_soc)) > 1e-8:
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _limiter_valid(record: Mapping[str, object]) -> bool:
    try:
        for row in _trace_rows(record):
            if row.get("bess_constraint_violations") != []:
                return False
            reasons = row.get("bess_saturation_reasons")
            if reasons != [[], [], [], []]:
                return False
            internal = row.get("bess_internal")
            if not isinstance(internal, Mapping):
                return False
            ipul = _vector(internal, "Ipul")
            ipcmd = _vector(internal, "Ipcmd_y")
            ipmin = _vector(internal, "Ipmin")
            ipmax = _vector(internal, "Ipmax")
            if not np.allclose(ipul, ipcmd, rtol=0.0, atol=POWER_ZERO_TOLERANCE):
                return False
            if np.any(ipcmd < ipmin - POWER_ZERO_TOLERANCE) or np.any(
                ipcmd > ipmax + POWER_ZERO_TOLERANCE
            ):
                return False
            for key in ("Fvl", "Fvh", "Ffl", "Ffh"):
                if not np.allclose(
                    _vector(internal, key), np.ones(4), rtol=0.0, atol=1e-12
                ):
                    return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _coordinate_trace(
    record: Mapping[str, object],
    point: Stage1OperatingPoint,
) -> np.ndarray:
    delta_frequency = np.asarray(
        [_vector(row, "delta_f_physical_hz") for row in _trace_rows(record)]
    )
    omega_deviation = delta_frequency / 60.0
    transform = weighted_common_differential_transform(
        np.full(4, point.vsg_m_system)
    )
    return (transform.forward @ omega_deviation.T).T


def _eval_integrity(scorecard: Mapping[str, object]) -> bool:
    try:
        validity = scorecard["validity"]
        evidence = scorecard["evidence_status"]
        source = scorecard["source"]
        return bool(
            isinstance(validity, Mapping)
            and validity.get("diagnostic_pass") is True
            and isinstance(validity.get("input_integrity"), Mapping)
            and validity["input_integrity"].get("pass") is True
            and isinstance(validity.get("execution_contract"), Mapping)
            and validity["execution_contract"].get("pass") is True
            and isinstance(evidence, Mapping)
            and evidence.get("status") == "EXTERNAL_AUTHORITY_REQUIRED"
            and isinstance(source, Mapping)
            and int(source.get("trace_count", -1)) == 18
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_stage1_records(
    records: Sequence[Mapping[str, object]],
    eval_scorecard: Mapping[str, object],
    *,
    expected_round: str = "R307",
    expected_question: str = "Q-0063",
    require_two_phase_solver: bool = False,
) -> dict[str, object]:
    """Fail-closed Stage-1 classification over the frozen 27-trace bank."""

    points = {point.name: point for point in stage1_operating_points()}
    coordinates = tuple(stage1_power_coordinates())
    expected_keys = {
        *((point, "zero", "zero") for point in points),
        *(
            (point, coordinate, sign)
            for point in points
            for coordinate in coordinates
            for sign in ("positive", "negative")
        ),
    }
    keyed: dict[tuple[str, str, str], Mapping[str, object]] = {}
    duplicate = False
    for record in records:
        key = (
            str(record.get("operating_point", "")),
            str(record.get("coordinate", "")),
            str(record.get("sign", "")),
        )
        if key in keyed:
            duplicate = True
        keyed[key] = record
    trace_matrix = not duplicate and set(keyed) == expected_keys and len(records) == 27
    eval_valid = _eval_integrity(eval_scorecard)

    guards: dict[str, bool] = {
        "trace_matrix_and_identity": trace_matrix,
        "execution_integrity": False,
        "power_path_authority": False,
        "md_readback": False,
        "achieved_power_tracking": False,
        "edge_neutrality": False,
        "soc_direction_and_bounds": False,
        "no_limiter_activation": False,
        "response_observable": False,
        "paired_local_linearity": False,
        "eval_diagnostic_integrity": eval_valid,
    }
    if require_two_phase_solver:
        guards["two_phase_solver_contract"] = False
    pair_metrics: dict[str, dict[str, float]] = {}
    if trace_matrix:
        all_records = list(keyed.values())
        guards["execution_integrity"] = all(
            _record_execution_valid(
                record,
                expected_round=expected_round,
                expected_question=expected_question,
            )
            for record in all_records
        )
        if require_two_phase_solver:
            guards["two_phase_solver_contract"] = all(
                _two_phase_solver_valid(record) for record in all_records
            )
        guards["power_path_authority"] = all(
            _power_layers_valid(record) for record in all_records
        )
        guards["md_readback"] = all(
            _md_readback_valid(record, points[str(record["operating_point"])])
            for record in all_records
        )
        guards["achieved_power_tracking"] = all(
            _achieved_power_valid(record) for record in all_records
        )
        guards["edge_neutrality"] = all(
            _edge_neutrality_valid(record) for record in all_records
        )
        guards["soc_direction_and_bounds"] = all(
            _soc_valid(record) for record in all_records
        )
        guards["no_limiter_activation"] = all(
            _limiter_valid(record) for record in all_records
        )
        try:
            for point_name, point in points.items():
                zero = _coordinate_trace(keyed[(point_name, "zero", "zero")], point)
                for coordinate in coordinates:
                    positive = keyed[(point_name, coordinate, "positive")]
                    negative = keyed[(point_name, coordinate, "negative")]
                    input_trace = np.asarray(
                        [
                            _vector(row, "bess_requested_power_system_pu")
                            for row in _trace_rows(positive)
                        ]
                    )
                    pair_metrics[f"{point_name}/{coordinate}"] = paired_response_metrics(
                        zero,
                        _coordinate_trace(positive, point),
                        _coordinate_trace(negative, point),
                        input_trace=input_trace,
                        input_kind="common" if coordinate == "common" else "edge",
                    )
        except (KeyError, TypeError, ValueError):
            pair_metrics = {}

    ratios = [row["signal_to_baseline_drift_ratio"] for row in pair_metrics.values()]
    nonlinearities = [row["midpoint_nonlinearity_ratio"] for row in pair_metrics.values()]
    op0_nonlinearities = [
        row["midpoint_nonlinearity_ratio"]
        for name, row in pair_metrics.items()
        if name.startswith("OP0/")
    ]
    guards["response_observable"] = len(ratios) == 12 and min(ratios) >= SIGNAL_TO_DRIFT_MIN
    guards["paired_local_linearity"] = bool(
        len(nonlinearities) == 12
        and max(op0_nonlinearities) <= OP0_NONLINEARITY_MAX
        and max(nonlinearities) <= ALL_POINT_NONLINEARITY_MAX
    )

    invalid_guards = (
        "trace_matrix_and_identity",
        "execution_integrity",
        "eval_diagnostic_integrity",
    )
    if require_two_phase_solver:
        invalid_guards += ("two_phase_solver_contract",)
    if not all(guards[name] for name in invalid_guards):
        classification = "INVALID-STAGE1-EXECUTION"
    elif all(guards.values()):
        classification = "STAGE1-PASS"
    else:
        classification = "STAGE1-AUTHORITY-NO-GO"
    return {
        "classification": classification,
        "guards": guards,
        "failures": [name for name, passed in guards.items() if not passed],
        "pair_metrics": pair_metrics,
        "max_op0_nonlinearity_ratio": (
            max(op0_nonlinearities) if op0_nonlinearities else None
        ),
        "max_all_nonlinearity_ratio": max(nonlinearities) if nonlinearities else None,
        "common_to_differential_gains": {
            name: row["cross_gain"]
            for name, row in pair_metrics.items()
            if name.endswith("/common")
        },
        "differential_to_common_gains": {
            name: row["cross_gain"]
            for name, row in pair_metrics.items()
            if "/edge_" in name
        },
        "predictor_eligible": classification == "STAGE1-PASS",
        "training_authorized": False,
        "claim_ceiling": "signed-authority-and-coupling-model-validation-only",
    }
