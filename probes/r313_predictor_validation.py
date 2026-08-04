"""Fail-closed R313 predictor validation and matched cross-block comparison.

This probe owns the claim-affecting record selection, physical validity, error
aggregation, and classification.  The execution adapter only resolves sealed
artifacts and writes this result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    Stage1OperatingPoint,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)
from andes_rl_kundur.evaluation.model_first_predictor import (
    predict_coordinate_response,
    response_error_metrics,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (
    synthesize_fresh_stage1_eval_guards,
)

ACTIVE_STEPS = 5
TOTAL_STEPS = 25
SAMPLE_PERIOD_SECONDS = 0.2
POWER_TOLERANCE = 1e-12
ZERO_TOLERANCE = 1e-8
MD_TOLERANCE = 1e-10
G_RESIDUAL_MAX = 1e-8
INITIALIZATION_TOLERANCE = 1e-4
INITIALIZATION_TINY = 1e-10
DYNAMIC_TOLERANCE = 1e-10
DYNAMIC_TINY = 1e-16


def aggregate_cross_value(
    *,
    full_cross_errors: Sequence[float],
    block_cross_errors: Sequence[float],
) -> dict[str, float | bool]:
    """Aggregate matched per-record cross-output L2 errors."""

    full = np.asarray(full_cross_errors, dtype=float)
    block = np.asarray(block_cross_errors, dtype=float)
    if (
        full.ndim != 1
        or block.shape != full.shape
        or full.size == 0
        or not np.all(np.isfinite(full))
        or not np.all(np.isfinite(block))
        or np.any(full < 0.0)
        or np.any(block < 0.0)
    ):
        raise ValueError("cross-error vectors must be matched finite nonnegative data")
    block_squared = float(np.sum(np.square(block)))
    full_squared = float(np.sum(np.square(full)))
    observable = block_squared > 1e-24
    reduction = (
        1.0 - full_squared / block_squared if observable else float("-inf")
    )
    return {
        "aggregate_full_cross_squared_error": full_squared,
        "aggregate_block_cross_squared_error": block_squared,
        "aggregate_cross_squared_error_reduction": reduction,
        "cross_record_win_fraction": float(np.mean(full < block)),
        "cross_signal_observable": observable,
    }


def classify_predictor_validation(
    *,
    execution_valid: bool,
    eval_valid: bool,
    metric_summary: Mapping[str, object] | None,
    thresholds: Mapping[str, float],
) -> dict[str, object]:
    """Apply the frozen INVALID/NO-GO/PASS tree."""

    if not execution_valid or not eval_valid:
        return {
            "classification": "INVALID-PREDICTOR-VALIDATION",
            "metric_guards": None,
        }
    if metric_summary is None:
        raise ValueError("valid execution requires a metric summary")
    guards = {
        "total_nrmse": float(metric_summary["max_total_nrmse"])
        <= float(thresholds["total_nrmse_max"]),
        "peak_magnitude_relative_error": float(
            metric_summary["max_peak_magnitude_relative_error"]
        )
        <= float(thresholds["peak_magnitude_relative_error_max"]),
        "peak_timing_error": float(
            metric_summary["max_peak_timing_error_seconds"]
        )
        <= float(thresholds["peak_timing_error_seconds_max"]),
        "aggregate_cross_value": float(
            metric_summary["aggregate_cross_squared_error_reduction"]
        )
        >= float(thresholds["aggregate_cross_squared_error_reduction_min"]),
        "cross_record_win_fraction": float(
            metric_summary["cross_record_win_fraction"]
        )
        >= float(thresholds["cross_record_win_fraction_min"]),
        "cross_signal_observable": bool(
            metric_summary["cross_signal_observable"]
        ),
    }
    return {
        "classification": (
            "PREDICTOR-PASS" if all(guards.values()) else "PREDICTOR-NO-GO"
        ),
        "metric_guards": guards,
    }


def _vector(row: Mapping[str, object], key: str) -> np.ndarray:
    values = np.asarray(row[key], dtype=float)
    if values.shape != (4,) or not np.all(np.isfinite(values)):
        raise ValueError(f"{key} must be a finite four-vector")
    return values


def _rows(record: Mapping[str, object]) -> list[Mapping[str, object]]:
    rows = record.get("traces")
    if not isinstance(rows, list) or len(rows) != TOTAL_STEPS:
        raise ValueError("record must contain exactly 25 trace rows")
    if not all(isinstance(row, Mapping) for row in rows):
        raise ValueError("every trace row must be an object")
    return rows


def _expected_request(
    record: Mapping[str, object],
    *,
    step: int,
) -> np.ndarray:
    coordinate = str(record["coordinate"])
    if coordinate == "zero" or step >= ACTIVE_STEPS:
        return np.zeros(4)
    sign = str(record["sign"])
    amplitude = float(record["pulse_amplitude_system_pu"])
    if sign not in {"positive", "negative"}:
        raise ValueError("nonzero record sign is invalid")
    vector = stage1_power_coordinates(amplitude)[coordinate]
    return vector * (1.0 if sign == "positive" else -1.0)


def _point_from_contract(entry: Mapping[str, object]) -> Stage1OperatingPoint:
    return Stage1OperatingPoint(
        name=str(entry["name"]),
        vsg_m_device=float(entry["vsg_m_device"]),
        vsg_d_device=float(entry["vsg_d_device"]),
        tie_rx_scale=float(entry["tie_rx_scale"]),
        initial_soc=float(entry["initial_soc"]),
    )


def _record_execution_valid(
    record: Mapping[str, object],
    *,
    point: Stage1OperatingPoint,
    expected_round: str,
    expected_question: str,
    expected_seal_sha256: str,
) -> bool:
    try:
        synthesize_fresh_stage1_eval_guards(record)
        rows = _rows(record)
        if (
            record.get("round") != expected_round
            or record.get("question") != expected_question
            or record.get("seal_sha256") != expected_seal_sha256
            or record.get("operating_point") != point.name
            or not np.isclose(
                float(record["initial_soc"]), point.initial_soc, rtol=0.0, atol=1e-12
            )
            or not np.allclose(
                np.asarray(record["initial_soc_readback"], dtype=float),
                np.full(4, point.initial_soc),
                rtol=0.0,
                atol=1e-10,
            )
        ):
            return False
        initialization = record["initialization_solver"]
        structural_initialization = record["structural"]["initialization_solver"]
        for source in (initialization, structural_initialization):
            if (
                not isinstance(source, Mapping)
                or source.get("tds_test_ok") is not True
                or int(source.get("system_exit_code", -1)) != 0
                or not np.isclose(
                    float(source["convergence_tolerance"]),
                    INITIALIZATION_TOLERANCE,
                    rtol=0.0,
                    atol=0.0,
                )
                or not np.isclose(
                    float(source["tiny_correction_threshold"]),
                    INITIALIZATION_TINY,
                    rtol=0.0,
                    atol=0.0,
                )
            ):
                return False
        times = np.asarray([float(row["t"]) for row in rows])
        if not np.allclose(
            np.diff(times), SAMPLE_PERIOD_SECONDS, rtol=0.0, atol=1e-9
        ):
            return False

        expected_m = np.full(4, point.vsg_m_system)
        expected_d = np.full(4, point.vsg_d_system)
        actual_power_rows: list[np.ndarray] = []
        soc_rows: list[np.ndarray] = []
        for step, row in enumerate(rows):
            expected = _expected_request(record, step=step)
            frequency = _vector(row, "freq_hz_physical")
            delta_frequency = _vector(row, "delta_f_physical_hz")
            if (
                row.get("pflow_converged") is not True
                or row.get("tds_failed") is not False
                or int(row.get("system_exit_code", -1)) != 0
                or row.get("finite_state_algebraic") is not True
                or float(row.get("dae_g_residual_max", np.inf)) > G_RESIDUAL_MAX
                or row.get("line_8_in_service") is not True
                or row.get("g4_in_service") is not True
                or float(row.get("g4_m_actual_system", 0.0)) <= 0.1
                or not np.allclose(
                    frequency - 60.0, delta_frequency, rtol=0.0, atol=1e-9
                )
                or not np.isclose(
                    float(row["tds_convergence_tolerance"]),
                    DYNAMIC_TOLERANCE,
                    rtol=0.0,
                    atol=0.0,
                )
                or not np.isclose(
                    float(row["tds_tiny_correction_threshold"]),
                    DYNAMIC_TINY,
                    rtol=0.0,
                    atol=0.0,
                )
                or int(row.get("md_write_count", -1)) != 0
                or not np.allclose(
                    _vector(row, "vsg_m_actual_system"),
                    expected_m,
                    rtol=0.0,
                    atol=MD_TOLERANCE,
                )
                or not np.allclose(
                    _vector(row, "vsg_d_actual_system"),
                    expected_d,
                    rtol=0.0,
                    atol=MD_TOLERANCE,
                )
            ):
                return False
            for key in (
                "bess_requested_power_system_pu",
                "bess_commanded_power_system_pu",
                "bess_external_command_readback_system_pu",
                "bess_internal_power_reference_system_pu",
            ):
                if not np.allclose(
                    _vector(row, key), expected, rtol=0.0, atol=POWER_TOLERANCE
                ):
                    return False
            if row.get("bess_constraint_violations") != [] or row.get(
                "bess_saturation_reasons"
            ) != [[], [], [], []]:
                return False
            internal = row.get("bess_internal")
            if not isinstance(internal, Mapping):
                return False
            ipul = _vector(internal, "Ipul")
            ipcmd = _vector(internal, "Ipcmd_y")
            ipmin = _vector(internal, "Ipmin")
            ipmax = _vector(internal, "Ipmax")
            if (
                not np.allclose(ipul, ipcmd, rtol=0.0, atol=ZERO_TOLERANCE)
                or np.any(ipcmd < ipmin - ZERO_TOLERANCE)
                or np.any(ipcmd > ipmax + ZERO_TOLERANCE)
                or any(
                    not np.allclose(
                        _vector(internal, key),
                        np.ones(4),
                        rtol=0.0,
                        atol=1e-12,
                    )
                    for key in ("Fvl", "Fvh", "Ffl", "Ffh")
                )
            ):
                return False
            actual_power_rows.append(
                _vector(row, "bess_actual_power_system_pu")
            )
            soc_rows.append(_vector(row, "bess_soc"))

        final_expected = _expected_request(record, step=ACTIVE_STEPS - 1)
        final_actual = actual_power_rows[ACTIVE_STEPS - 1]
        active = np.abs(final_expected) > ZERO_TOLERANCE
        if np.any(active):
            if (
                np.any(final_actual[active] * final_expected[active] <= 0.0)
                or np.any(
                    np.abs(final_actual[active] - final_expected[active])
                    > 0.05 * np.abs(final_expected[active])
                )
                or np.any(np.abs(final_actual[~active]) > ZERO_TOLERANCE)
            ):
                return False
        elif np.max(np.abs(final_actual)) > ZERO_TOLERANCE:
            return False
        if str(record["coordinate"]).startswith("edge_"):
            if any(
                abs(float(np.sum(_expected_request(record, step=step))))
                > POWER_TOLERANCE
                for step in range(TOTAL_STEPS)
            ):
                return False
            if abs(float(np.sum(final_actual))) > 0.05 * float(
                np.sum(np.abs(final_expected))
            ):
                return False

        soc = np.asarray(soc_rows)
        actual_power = np.asarray(actual_power_rows)
        if np.min(soc) < 0.2 or np.max(soc) > 0.8:
            return False
        energy_sign = np.sum(actual_power, axis=0)
        delta_soc = soc[-1] - point.initial_soc
        positive = energy_sign > ZERO_TOLERANCE
        negative = energy_sign < -ZERO_TOLERANCE
        if (
            np.any(delta_soc[positive] >= 0.0)
            or np.any(delta_soc[negative] <= 0.0)
            or (
                not np.any(positive | negative)
                and np.max(np.abs(delta_soc)) > ZERO_TOLERANCE
            )
        ):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _coordinate_trace(
    record: Mapping[str, object],
    point: Stage1OperatingPoint,
) -> np.ndarray:
    frequency = np.asarray(
        [_vector(row, "delta_f_physical_hz") for row in _rows(record)]
    )
    transform = weighted_common_differential_transform(
        np.full(4, point.vsg_m_system)
    )
    return (transform.forward @ (frequency / 60.0).T).T


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
            and int(source.get("trace_count", -1)) == 24
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_predictor_validation(
    records: Sequence[Mapping[str, object]],
    model: Mapping[str, object],
    eval_scorecard: Mapping[str, object],
    contract: Mapping[str, object],
    *,
    expected_round: str = "R313",
    expected_question: str = "Q-0069",
    expected_seal_sha256: str,
    model_provenance_valid: bool,
) -> dict[str, object]:
    """Evaluate the frozen 34-trace holdout and matched predictor arms."""

    point_entries = contract.get("holdout_operating_points")
    amplitudes = contract.get("holdout_amplitudes_system_pu")
    thresholds = contract.get("thresholds")
    if (
        not isinstance(point_entries, list)
        or not isinstance(amplitudes, list)
        or not isinstance(thresholds, Mapping)
    ):
        raise ValueError("predictor contract is incomplete")
    points = {
        str(entry["name"]): (_point_from_contract(entry), entry)
        for entry in point_entries
        if isinstance(entry, Mapping)
    }
    coordinates = tuple(stage1_power_coordinates())
    expected_keys = {
        *((point, "zero", "zero", 0.0) for point in points),
        *(
            (point, coordinate, sign, float(amplitude))
            for point in points
            for coordinate in coordinates
            for sign in ("positive", "negative")
            for amplitude in amplitudes
        ),
    }
    keyed: dict[tuple[str, str, str, float], Mapping[str, object]] = {}
    for record in records:
        key = (
            str(record.get("operating_point", "")),
            str(record.get("coordinate", "")),
            str(record.get("sign", "")),
            float(record.get("pulse_amplitude_system_pu", float("nan"))),
        )
        if key in keyed:
            key = ("duplicate", "", "", float("nan"))
            break
        keyed[key] = record
    identity_valid = set(keyed) == expected_keys and len(records) == 34
    model_authority = contract.get("model_authority")
    if isinstance(model_authority, Mapping):
        training_model_valid = bool(
            model_provenance_valid
            and all(
                model.get(key) == expected
                for key, expected in model_authority.items()
            )
            and model.get("controller_development_authorized") is False
            and model.get("training_authorized") is False
        )
    else:
        training_model_valid = bool(
            model_provenance_valid
            and model.get("training_round") == "R312"
            and model.get("training_question") == "Q-0068"
            and model.get("training_trace_count") == 27
            and model.get("controller_development_authorized") is False
            and model.get("training_authorized") is False
        )
    record_validity: dict[str, bool] = {}
    if identity_valid:
        for key, record in keyed.items():
            point = points[key[0]][0]
            label = "/".join((key[0], key[1], key[2], f"{key[3]:.3f}"))
            record_validity[label] = _record_execution_valid(
                record,
                point=point,
                expected_round=expected_round,
                expected_question=expected_question,
                expected_seal_sha256=expected_seal_sha256,
            )
    execution_guards = {
        "exact_holdout_identity": identity_valid,
        "sealed_r312_only_model": training_model_valid,
        "all_physical_records_valid": bool(record_validity)
        and all(record_validity.values()),
    }
    execution_valid = all(execution_guards.values())
    eval_valid = _eval_integrity(eval_scorecard)
    if not execution_valid or not eval_valid:
        classified = classify_predictor_validation(
            execution_valid=execution_valid,
            eval_valid=eval_valid,
            metric_summary=None,
            thresholds=thresholds,
        )
        return {
            **classified,
            "execution_guards": execution_guards,
            "record_validity": record_validity,
            "eval_integrity": eval_valid,
            "metric_summary": None,
            "cases": [],
            "claim_ceiling": "invalid-no-predictor-effect-interpretation",
            "controller_development_authorized": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
        }

    cases: list[dict[str, object]] = []
    full_cross_errors: list[float] = []
    block_cross_errors: list[float] = []
    for point_name, (point, point_entry) in points.items():
        baseline = _coordinate_trace(
            keyed[(point_name, "zero", "zero", 0.0)], point
        )
        weights = point_entry["training_weights"]
        for coordinate in coordinates:
            for sign in ("positive", "negative"):
                direction = 1.0 if sign == "positive" else -1.0
                for amplitude_value in amplitudes:
                    amplitude = float(amplitude_value)
                    record = keyed[(point_name, coordinate, sign, amplitude)]
                    actual = _coordinate_trace(record, point) - baseline
                    full_prediction = predict_coordinate_response(
                        model,
                        weights=weights,
                        coordinate=coordinate,
                        signed_amplitude_system_pu=direction * amplitude,
                        arm="full",
                    )
                    block_prediction = predict_coordinate_response(
                        model,
                        weights=weights,
                        coordinate=coordinate,
                        signed_amplitude_system_pu=direction * amplitude,
                        arm="block_diagonal",
                    )
                    full_metrics = response_error_metrics(
                        actual,
                        full_prediction,
                        coordinate=coordinate,
                        sample_period_seconds=SAMPLE_PERIOD_SECONDS,
                    )
                    block_metrics = response_error_metrics(
                        actual,
                        block_prediction,
                        coordinate=coordinate,
                        sample_period_seconds=SAMPLE_PERIOD_SECONDS,
                    )
                    full_cross_errors.append(full_metrics["cross_error_l2"])
                    block_cross_errors.append(block_metrics["cross_error_l2"])
                    cases.append(
                        {
                            "operating_point": point_name,
                            "coordinate": coordinate,
                            "sign": sign,
                            "amplitude_system_pu": amplitude,
                            "full": full_metrics,
                            "block_diagonal": block_metrics,
                        }
                    )

    cross_summary = aggregate_cross_value(
        full_cross_errors=full_cross_errors,
        block_cross_errors=block_cross_errors,
    )
    metric_summary: dict[str, object] = {
        "max_total_nrmse": max(float(case["full"]["total_nrmse"]) for case in cases),
        "max_peak_magnitude_relative_error": max(
            float(case["full"]["peak_magnitude_relative_error"])
            for case in cases
        ),
        "max_peak_timing_error_seconds": max(
            float(case["full"]["peak_timing_error_seconds"])
            for case in cases
        ),
        **cross_summary,
    }
    strata = {
        "by_operating_point": {
            point: max(
                float(case["full"]["total_nrmse"])
                for case in cases
                if case["operating_point"] == point
            )
            for point in points
        },
        "by_amplitude_system_pu": {
            f"{float(amplitude):.3f}": max(
                float(case["full"]["total_nrmse"])
                for case in cases
                if float(case["amplitude_system_pu"]) == float(amplitude)
            )
            for amplitude in amplitudes
        },
    }
    classified = classify_predictor_validation(
        execution_valid=True,
        eval_valid=True,
        metric_summary=metric_summary,
        thresholds=thresholds,
    )
    return {
        **classified,
        "execution_guards": execution_guards,
        "record_validity": record_validity,
        "eval_integrity": True,
        "metric_summary": metric_summary,
        "strata": strata,
        "cases": cases,
        "claim_ceiling": (
            "sealed-finite-horizon-convex-holdout-pulse-response-only"
        ),
        "comparison_identifiability": contract["comparison_identifiability"],
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
