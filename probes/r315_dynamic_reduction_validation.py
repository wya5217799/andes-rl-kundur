"""Fail-closed R315 dynamic-reduction and mismatch-set validation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    Stage1OperatingPoint,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)
from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    realization_from_dict,
    simulate_mimo_fir_response,
    simulate_state_space,
)
from andes_rl_kundur.evaluation.model_first_stage1_eval_guards import (
    synthesize_fresh_stage1_eval_guards,
)
from probes.r313_predictor_validation import aggregate_cross_value

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


def classify_dynamic_reduction(
    *,
    execution_valid: bool,
    eval_valid: bool,
    metric_summary: Mapping[str, object] | None,
    thresholds: Mapping[str, float],
) -> dict[str, object]:
    """Apply the frozen INVALID/NO-GO/PASS decision tree."""

    if not execution_valid or not eval_valid:
        return {
            "classification": "INVALID-DYNAMIC-REDUCTION-VALIDATION",
            "metric_guards": None,
        }
    if metric_summary is None:
        raise ValueError("valid execution requires a metric summary")
    guards = {
        "parent_physical_total_nrmse": float(
            metric_summary["max_parent_physical_total_nrmse"]
        )
        <= float(thresholds["parent_physical_total_nrmse_max"]),
        "reduced_parent_total_nrmse": float(
            metric_summary["max_reduced_parent_total_nrmse"]
        )
        <= float(thresholds["reduced_parent_total_nrmse_max"]),
        "reduced_physical_total_nrmse": float(
            metric_summary["max_reduced_physical_total_nrmse"]
        )
        <= float(thresholds["reduced_physical_total_nrmse_max"]),
        "maximum_normalized_absolute_residual": float(
            metric_summary["max_normalized_absolute_residual"]
        )
        <= float(thresholds["maximum_normalized_absolute_residual_max"]),
        "peak_magnitude_relative_error": float(
            metric_summary["max_peak_magnitude_relative_error"]
        )
        <= float(thresholds["peak_magnitude_relative_error_max"]),
        "peak_timing_error": float(
            metric_summary["max_peak_timing_error_seconds"]
        )
        <= float(thresholds["peak_timing_error_seconds_max"]),
        "maximum_spectral_radius": float(
            metric_summary["maximum_spectral_radius"]
        )
        <= float(thresholds["maximum_spectral_radius"]) + 1e-10,
        "aggregate_cross_value": float(
            metric_summary["aggregate_cross_squared_error_reduction"]
        )
        >= float(thresholds["aggregate_cross_squared_error_reduction_min"]),
        "cross_record_win_fraction": float(
            metric_summary["cross_record_win_fraction"]
        )
        >= float(thresholds["cross_record_win_fraction_min"]),
        "cross_signal_observable": bool(metric_summary["cross_signal_observable"]),
    }
    return {
        "classification": (
            "DYNAMIC-REDUCTION-PASS"
            if all(guards.values())
            else "DYNAMIC-REDUCTION-NO-GO"
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


def _point_from_contract(entry: Mapping[str, object]) -> Stage1OperatingPoint:
    return Stage1OperatingPoint(
        name=str(entry["name"]),
        vsg_m_device=float(entry["vsg_m_device"]),
        vsg_d_device=float(entry["vsg_d_device"]),
        tie_rx_scale=float(entry["tie_rx_scale"]),
        initial_soc=float(entry["initial_soc"]),
    )


def _signed_scalar_sequence(
    *,
    shape: str,
    sign: str,
    excitation_shapes: Mapping[str, object],
) -> np.ndarray:
    if shape == "zero":
        if sign != "zero":
            raise ValueError("zero shape requires zero sign")
        return np.zeros(TOTAL_STEPS)
    if shape not in excitation_shapes or sign not in {"positive", "negative"}:
        raise ValueError("record shape/sign is outside the contract")
    base = np.asarray(excitation_shapes[shape], dtype=float)
    if base.ndim != 1 or not 1 <= base.size <= TOTAL_STEPS:
        raise ValueError("excitation shape is invalid")
    result = np.zeros(TOTAL_STEPS)
    result[: base.size] = base * (1.0 if sign == "positive" else -1.0)
    return result


def _expected_requests(coordinate: str, sequence: np.ndarray) -> np.ndarray:
    if coordinate == "zero":
        return np.zeros((TOTAL_STEPS, 4))
    coordinates = stage1_power_coordinates(1.0)
    if coordinate not in coordinates:
        raise ValueError("unknown action coordinate")
    return sequence[:, None] * np.asarray(coordinates[coordinate], dtype=float)[None, :]


def _record_execution_valid(
    record: Mapping[str, object],
    *,
    point: Stage1OperatingPoint,
    excitation_shapes: Mapping[str, object],
    expected_round: str,
    expected_question: str,
    expected_seal_sha256: str,
    expected_model_sha256: str,
) -> bool:
    try:
        synthesize_fresh_stage1_eval_guards(record)
        rows = _rows(record)
        shape = str(record["input_shape"])
        sign = str(record["sign"])
        coordinate = str(record["coordinate"])
        sequence = _signed_scalar_sequence(
            shape=shape, sign=sign, excitation_shapes=excitation_shapes
        )
        expected_requests = _expected_requests(coordinate, sequence)
        if (
            record.get("round") != expected_round
            or record.get("question") != expected_question
            or record.get("seal_sha256") != expected_seal_sha256
            or record.get("dynamic_model_sha256") != expected_model_sha256
            or record.get("operating_point") != point.name
            or record.get("controller") != sign
            or not np.isclose(
                float(record["initial_soc"]), point.initial_soc, rtol=0.0, atol=1e-12
            )
            or not np.allclose(
                np.asarray(record["initial_soc_readback"], dtype=float),
                np.full(4, point.initial_soc),
                rtol=0.0,
                atol=1e-10,
            )
            or not np.allclose(
                np.asarray(record["input_sequence_system_pu"], dtype=float),
                sequence,
                rtol=0.0,
                atol=1e-15,
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
        soc_rows: list[np.ndarray] = []
        for step, row in enumerate(rows):
            expected = expected_requests[step]
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
            actual = _vector(row, "bess_actual_power_system_pu")
            active = np.abs(expected) > ZERO_TOLERANCE
            if (
                np.any(active)
                and (
                    np.any(actual[active] * expected[active] <= 0.0)
                    or np.any(
                        np.abs(actual[active] - expected[active])
                        > 0.05 * np.abs(expected[active])
                    )
                    or np.any(np.abs(actual[~active]) > ZERO_TOLERANCE)
                )
            ) or (not np.any(active) and np.max(np.abs(actual)) > ZERO_TOLERANCE):
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
            soc_rows.append(_vector(row, "bess_soc"))
        if coordinate.startswith("edge_") and np.max(
            np.abs(np.sum(expected_requests, axis=1))
        ) > POWER_TOLERANCE:
            return False
        soc = np.asarray(soc_rows)
        if np.min(soc) < 0.2 or np.max(soc) > 0.8:
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def _coordinate_trace(
    record: Mapping[str, object], point: Stage1OperatingPoint
) -> np.ndarray:
    frequency = np.asarray(
        [_vector(row, "delta_f_physical_hz") for row in _rows(record)]
    )
    transform = weighted_common_differential_transform(
        np.full(4, point.vsg_m_system)
    )
    return (transform.forward @ (frequency / 60.0).T).T


def _input_matrix(coordinate: str, scalar_sequence: np.ndarray) -> np.ndarray:
    names = tuple(stage1_power_coordinates())
    matrix = np.zeros((TOTAL_STEPS, len(names)))
    matrix[:, names.index(coordinate)] = scalar_sequence
    return matrix


def _response_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    *,
    coordinate: str,
    normalization: np.ndarray | None = None,
) -> dict[str, float]:
    if actual.shape != (TOTAL_STEPS, 4) or predicted.shape != actual.shape:
        raise ValueError("dynamic responses must be 25-by-4")
    reference = actual if normalization is None else normalization
    error = predicted - actual
    names = tuple(stage1_power_coordinates())
    direct_index = names.index(coordinate)
    actual_direct = np.abs(actual[:, direct_index])
    predicted_direct = np.abs(predicted[:, direct_index])
    actual_peak = float(np.max(actual_direct))
    predicted_peak = float(np.max(predicted_direct))
    cross_indices = [1, 2, 3] if coordinate == "common" else [0]
    return {
        "total_nrmse": float(np.linalg.norm(error))
        / max(float(np.linalg.norm(reference)), 1e-15),
        "maximum_normalized_absolute_residual": float(np.max(np.abs(error)))
        / max(float(np.max(np.abs(reference))), 1e-15),
        "peak_magnitude_relative_error": abs(predicted_peak - actual_peak)
        / max(actual_peak, 1e-15),
        "peak_timing_error_seconds": abs(
            int(np.argmax(predicted_direct)) - int(np.argmax(actual_direct))
        )
        * SAMPLE_PERIOD_SECONDS,
        "cross_actual_l2": float(np.linalg.norm(actual[:, cross_indices])),
        "cross_error_l2": float(np.linalg.norm(error[:, cross_indices])),
    }


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
            and int(source.get("trace_count", -1)) == 36
        )
    except (KeyError, TypeError, ValueError):
        return False


def evaluate_dynamic_reduction_validation(
    records: Sequence[Mapping[str, object]],
    model: Mapping[str, object],
    eval_scorecard: Mapping[str, object],
    contract: Mapping[str, object],
    *,
    expected_seal_sha256: str,
    expected_model_sha256: str,
    model_provenance_valid: bool,
) -> dict[str, object]:
    """Evaluate the frozen 50-trace physical mismatch bank."""

    point_entries = contract.get("holdout_operating_points")
    shapes = contract.get("excitation_shapes")
    thresholds = contract.get("thresholds")
    if (
        not isinstance(point_entries, list)
        or not isinstance(shapes, Mapping)
        or not isinstance(thresholds, Mapping)
    ):
        raise ValueError("dynamic-reduction contract is incomplete")
    points = {
        str(entry["name"]): (_point_from_contract(entry), entry)
        for entry in point_entries
        if isinstance(entry, Mapping)
    }
    coordinates = tuple(stage1_power_coordinates())
    expected_keys = {
        *((point, "zero", "zero", "zero") for point in points),
        *(
            (point, shape, coordinate, sign)
            for point in points
            for shape in shapes
            for coordinate in coordinates
            for sign in ("positive", "negative")
        ),
    }
    keyed: dict[tuple[str, str, str, str], Mapping[str, object]] = {}
    for record in records:
        key = (
            str(record.get("operating_point", "")),
            str(record.get("input_shape", "")),
            str(record.get("coordinate", "")),
            str(record.get("sign", "")),
        )
        if key in keyed:
            key = ("duplicate", "", "", "")
            break
        keyed[key] = record
    identity_valid = set(keyed) == expected_keys and len(records) == 50
    model_points = model.get("points")
    model_valid = bool(
        model_provenance_valid
        and model.get("round") == "R315"
        and model.get("question") == "Q-0071"
        and model.get("R314_holdout_used_for_fitting") is False
        and model.get("R315_holdout_accessed") is False
        and model.get("controller_development_authorized") is False
        and model.get("training_authorized") is False
        and isinstance(model_points, Mapping)
        and set(model_points) == set(points)
    )
    record_validity: dict[str, bool] = {}
    if identity_valid:
        for key, record in keyed.items():
            point = points[key[0]][0]
            label = "/".join(key)
            record_validity[label] = _record_execution_valid(
                record,
                point=point,
                excitation_shapes=shapes,
                expected_round="R315",
                expected_question="Q-0071",
                expected_seal_sha256=expected_seal_sha256,
                expected_model_sha256=expected_model_sha256,
            )
    execution_guards = {
        "exact_holdout_identity": identity_valid,
        "sealed_development_only_model": model_valid,
        "all_physical_records_valid": bool(record_validity)
        and all(record_validity.values()),
    }
    execution_valid = all(execution_guards.values())
    eval_valid = _eval_integrity(eval_scorecard)
    if not execution_valid or not eval_valid:
        classified = classify_dynamic_reduction(
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
            "claim_ceiling": "invalid-no-model-effect-interpretation",
            "controller_development_authorized": False,
            "distributed_agent_implementation_authorized": False,
            "training_authorized": False,
        }

    cases: list[dict[str, object]] = []
    full_cross_errors: list[float] = []
    block_cross_errors: list[float] = []
    maximum_radius = 0.0
    for point_name, (point, _point_entry) in points.items():
        point_model = model_points[point_name]
        if not isinstance(point_model, Mapping):
            raise ValueError("dynamic model point entry is invalid")
        markov = np.asarray(point_model["markov_parameters"], dtype=float)
        realization = realization_from_dict(point_model["realization"])
        maximum_radius = max(maximum_radius, realization.spectral_radius)
        baseline = _coordinate_trace(
            keyed[(point_name, "zero", "zero", "zero")], point
        )
        for shape in shapes:
            for coordinate in coordinates:
                for sign in ("positive", "negative"):
                    record = keyed[(point_name, shape, coordinate, sign)]
                    actual = _coordinate_trace(record, point) - baseline
                    scalar = _signed_scalar_sequence(
                        shape=shape, sign=sign, excitation_shapes=shapes
                    )
                    inputs = _input_matrix(coordinate, scalar)
                    parent_prediction = simulate_mimo_fir_response(markov, inputs)
                    reduced_prediction = simulate_state_space(realization, inputs)
                    block_prediction = reduced_prediction.copy()
                    if coordinate == "common":
                        block_prediction[:, 1:] = 0.0
                    else:
                        block_prediction[:, 0] = 0.0
                    parent_metrics = _response_metrics(
                        actual, parent_prediction, coordinate=coordinate
                    )
                    reduced_metrics = _response_metrics(
                        actual, reduced_prediction, coordinate=coordinate
                    )
                    reduction_metrics = _response_metrics(
                        parent_prediction,
                        reduced_prediction,
                        coordinate=coordinate,
                        normalization=parent_prediction,
                    )
                    block_metrics = _response_metrics(
                        actual, block_prediction, coordinate=coordinate
                    )
                    full_cross_errors.append(reduced_metrics["cross_error_l2"])
                    block_cross_errors.append(block_metrics["cross_error_l2"])
                    cases.append(
                        {
                            "operating_point": point_name,
                            "input_shape": shape,
                            "coordinate": coordinate,
                            "sign": sign,
                            "parent_physical": parent_metrics,
                            "reduced_physical": reduced_metrics,
                            "reduced_parent": reduction_metrics,
                            "block_physical": block_metrics,
                        }
                    )
    cross_summary = aggregate_cross_value(
        full_cross_errors=full_cross_errors,
        block_cross_errors=block_cross_errors,
    )
    metric_summary: dict[str, object] = {
        "max_parent_physical_total_nrmse": max(
            float(case["parent_physical"]["total_nrmse"]) for case in cases
        ),
        "max_reduced_parent_total_nrmse": max(
            float(case["reduced_parent"]["total_nrmse"]) for case in cases
        ),
        "max_reduced_physical_total_nrmse": max(
            float(case["reduced_physical"]["total_nrmse"]) for case in cases
        ),
        "max_normalized_absolute_residual": max(
            float(
                case["reduced_physical"][
                    "maximum_normalized_absolute_residual"
                ]
            )
            for case in cases
        ),
        "max_peak_magnitude_relative_error": max(
            float(case["reduced_physical"]["peak_magnitude_relative_error"])
            for case in cases
        ),
        "max_peak_timing_error_seconds": max(
            float(case["reduced_physical"]["peak_timing_error_seconds"])
            for case in cases
        ),
        "maximum_spectral_radius": maximum_radius,
        **cross_summary,
    }
    strata = {
        "by_operating_point": {
            point: max(
                float(case["reduced_physical"]["total_nrmse"])
                for case in cases
                if case["operating_point"] == point
            )
            for point in points
        },
        "by_input_shape": {
            shape: max(
                float(case["reduced_physical"]["total_nrmse"])
                for case in cases
                if case["input_shape"] == shape
            )
            for shape in shapes
        },
        "by_coordinate": {
            coordinate: max(
                float(case["reduced_physical"]["total_nrmse"])
                for case in cases
                if case["coordinate"] == coordinate
            )
            for coordinate in coordinates
        },
    }
    classified = classify_dynamic_reduction(
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
            "sealed-two-point-small-signal-off-template-dynamic-mismatch-only"
        ),
        "comparison_identifiability": contract["comparison_identifiability"],
        "controller_development_authorized": False,
        "distributed_agent_implementation_authorized": False,
        "training_authorized": False,
    }
