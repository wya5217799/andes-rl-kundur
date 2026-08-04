"""Pure fit and decision logic for the R335 physical disturbance package."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    realization_from_dict,
    simulate_state_space,
)


def _finite_matrix(value: object, *, name: str) -> np.ndarray:
    matrix = np.asarray(value, dtype=float)
    if matrix.ndim != 2 or not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must be a finite matrix")
    return matrix


def fit_r335_disturbance_map(
    *,
    contract: Mapping[str, Any],
    development_records: Sequence[Mapping[str, Any]],
    realization_payload: Mapping[str, Any],
) -> dict[str, object]:
    """Fit one cross-coupled coordinate column per physical load channel."""

    development_point = str(contract["development_point"])
    channels = tuple(str(value) for value in contract["channels"])
    shapes = {
        str(name): np.asarray(values, dtype=float)
        for name, values in dict(contract["shapes"]).items()
    }
    total_steps = int(contract["total_steps"])
    if len(channels) != 4 or len(set(channels)) != 4:
        raise ValueError("contract must declare four unique channels")
    if total_steps < 1 or not shapes:
        raise ValueError("contract must declare finite shapes and total_steps")
    if any(
        values.ndim != 1
        or values.size < 1
        or values.size > total_steps
        or not np.all(np.isfinite(values))
        for values in shapes.values()
    ):
        raise ValueError("each shape must be a finite vector within total_steps")
    if any(str(row.get("operating_point")) != development_point for row in development_records):
        raise ValueError("fit input contains a non-development record")

    realization = realization_from_dict(dict(realization_payload))
    expected_keys = {
        (channel, shape, sign)
        for channel in channels
        for shape in shapes
        for sign in ("positive", "negative")
    }
    expected_inventory = expected_keys | {("zero", "zero", "zero")}
    rows: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    for row in development_records:
        key = (
            str(row.get("channel")),
            str(row.get("shape")),
            str(row.get("sign")),
        )
        if key in rows:
            raise ValueError(f"duplicate development fit record: {key}")
        rows[key] = row
    if set(rows) != expected_inventory or len(development_records) != len(
        expected_inventory
    ):
        raise ValueError("development fit inventory is incomplete or duplicated")

    design_by_shape: dict[str, np.ndarray] = {}
    for shape, active in shapes.items():
        profile = np.zeros(total_steps, dtype=float)
        profile[: active.size] = active
        columns = []
        for coordinate in range(4):
            inputs = np.zeros((total_steps, 4), dtype=float)
            inputs[:, coordinate] = profile
            columns.append(simulate_state_space(realization, inputs).reshape(-1))
        design_by_shape[shape] = np.column_stack(columns)

    coordinate_map = np.zeros((4, 4), dtype=float)
    for column, channel in enumerate(channels):
        design_rows: list[np.ndarray] = []
        response_rows: list[np.ndarray] = []
        for shape in shapes:
            positive = _finite_matrix(
                rows[(channel, shape, "positive")]["output_coordinates"],
                name=f"{channel}/{shape}/positive output",
            )
            negative = _finite_matrix(
                rows[(channel, shape, "negative")]["output_coordinates"],
                name=f"{channel}/{shape}/negative output",
            )
            if positive.shape != (total_steps, 4) or negative.shape != positive.shape:
                raise ValueError("development output shape does not match the contract")
            design_rows.append(design_by_shape[shape])
            response_rows.append((0.5 * (positive - negative)).reshape(-1))
        design = np.vstack(design_rows)
        response = np.concatenate(response_rows)
        solution, _, rank, _ = np.linalg.lstsq(design, response, rcond=None)
        if rank != 4 or not np.all(np.isfinite(solution)):
            raise ValueError("development design is rank-deficient or non-finite")
        coordinate_map[:, column] = solution

    return {
        "schema_version": 1,
        "development_point": development_point,
        "coordinate_map": coordinate_map.tolist(),
        "fit_record_count": len(expected_keys),
        "holdout_records_accessed": False,
        "fit_method": "unregularized-joint-signed-waveform-least-squares",
    }


def _record_index(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[tuple[str, str, str], Mapping[str, Any]], bool]:
    index: dict[tuple[str, str, str], Mapping[str, Any]] = {}
    duplicate = False
    for row in records:
        key = (
            str(row.get("channel")),
            str(row.get("shape")),
            str(row.get("sign")),
        )
        if key in index:
            duplicate = True
            continue
        index[key] = row
    return index, duplicate


def _prediction_metrics(physical: np.ndarray, predicted: np.ndarray) -> dict[str, float]:
    error = predicted - physical
    response_norm = float(np.linalg.norm(physical))
    peak_response = float(np.max(np.linalg.norm(physical, axis=1)))
    if response_norm <= 0.0 or peak_response <= 0.0:
        return {"total_nrmse": 1.0e300, "peak_vector_residual": 1.0e300}
    return {
        "total_nrmse": float(np.linalg.norm(error) / response_norm),
        "peak_vector_residual": float(
            np.max(np.linalg.norm(error, axis=1)) / peak_response
        ),
    }


def analyse_r335_disturbance_package(
    *,
    contract: Mapping[str, Any],
    development_records: Sequence[Mapping[str, Any]],
    holdout_records: Sequence[Mapping[str, Any]],
    fit_payload: Mapping[str, Any],
    realization_payloads: Mapping[str, Mapping[str, Any]],
    execution_validity: Mapping[str, Any],
) -> dict[str, object]:
    """Classify the frozen R335 development/holdout disturbance package."""

    round_id = str(contract["round"])
    question_id = str(contract["question"])
    development_point = str(contract["development_point"])
    holdout_point = str(contract["holdout_point"])
    channels = tuple(str(value) for value in contract["channels"])
    shapes = {
        str(name): np.asarray(values, dtype=float)
        for name, values in dict(contract["shapes"]).items()
    }
    total_steps = int(contract["total_steps"])
    thresholds = dict(contract["thresholds"])
    basis = _finite_matrix(contract["node_input_basis"], name="node_input_basis")
    raw_coordinate_map = np.asarray(fit_payload.get("coordinate_map"), dtype=float)
    coordinate_map_guard = bool(
        raw_coordinate_map.shape == (4, 4)
        and np.all(np.isfinite(raw_coordinate_map))
    )
    coordinate_map = (
        raw_coordinate_map if coordinate_map_guard else np.zeros((4, 4), dtype=float)
    )
    if basis.shape != (4, 4):
        raise ValueError("R335 basis and fitted map must be four-by-four")

    development_index, development_duplicate = _record_index(development_records)
    holdout_index, holdout_duplicate = _record_index(holdout_records)
    expected_keys = {("zero", "zero", "zero")}
    expected_keys.update(
        (channel, shape, sign)
        for channel in channels
        for shape in shapes
        for sign in ("positive", "negative")
    )
    all_records = list(development_records) + list(holdout_records)
    identity_guard = all(
        str(row.get("round")) == round_id
        and str(row.get("question")) == question_id
        for row in all_records
    )
    inventory_guard = (
        set(development_index) == expected_keys
        and set(holdout_index) == expected_keys
        and len(development_records) == len(expected_keys)
        and len(holdout_records) == len(expected_keys)
        and not development_duplicate
        and not holdout_duplicate
    )
    point_guard = all(
        str(row.get("operating_point")) == development_point
        for row in development_records
    ) and all(
        str(row.get("operating_point")) == holdout_point
        for row in holdout_records
    )
    record_guard = all(row.get("record_valid") is True for row in all_records)
    numeric_record_guard = all(
        np.asarray(row.get("output_coordinates"), dtype=float).shape
        == (total_steps, 4)
        and np.all(np.isfinite(np.asarray(row.get("output_coordinates"), dtype=float)))
        for row in all_records
    )
    reward_boundary_guard = all(
        row.get("reward_diagnostics_computed") is True
        and row.get("reward_diagnostics_stored") is True
        and row.get("reward_used_for_action") is False
        and row.get("reward_used_for_fitting") is False
        and row.get("reward_used_for_selection") is False
        and row.get("reward_used_for_training") is False
        and row.get("reward_used_for_classification") is False
        and row.get("reward_used_for_claim") is False
        for row in all_records
    )
    fit_boundary_guard = (
        str(fit_payload.get("round")) == round_id
        and str(fit_payload.get("question")) == question_id
        and str(fit_payload.get("development_point")) == development_point
        and fit_payload.get("holdout_records_accessed") is False
        and fit_payload.get("fit_created_before_holdout") is True
        and int(fit_payload.get("fit_record_count", -1))
        == 2 * len(channels) * len(shapes)
    )
    execution_guard = execution_validity.get("all_guards_pass") is True
    validity_guards = {
        "identity": identity_guard,
        "strict_inventory": inventory_guard,
        "operating_point_split": point_guard,
        "record_execution": record_guard,
        "finite_record_outputs": numeric_record_guard,
        "reward_boundary": reward_boundary_guard,
        "fit_before_holdout": fit_boundary_guard,
        "execution_chain": execution_guard,
        "finite_fitted_map": coordinate_map_guard,
    }

    if not all(validity_guards.values()):
        return {
            "schema_version": 1,
            "round": round_id,
            "question": question_id,
            "classification": "INVALID-PHYSICAL-DISTURBANCE-PACKAGE",
            "validity_guards": validity_guards,
            "identification_guards": {},
            "record_metrics": {},
            "pair_metrics": {},
            "package_metrics": {},
            "holdout_used_for_fitting": False,
            "scope": {
                "controller_executed": False,
                "closed_loop_executed": False,
                "distributed_runtime_executed": False,
                "training_executed": False,
                "eval_executed": False,
                "title_changed": False,
            },
        }

    realizations = {
        point: realization_from_dict(dict(realization_payloads[point]))
        for point in (development_point, holdout_point)
    }
    indices = {
        development_point: development_index,
        holdout_point: holdout_index,
    }
    record_metrics: dict[str, dict[str, object]] = {}
    pair_metrics: dict[str, dict[str, float]] = {}
    signal_pass = True
    sign_pass = True
    pair_pass = True
    development_prediction_pass = True
    holdout_prediction_pass = True

    for point in (development_point, holdout_point):
        zero = _finite_matrix(
            indices[point][("zero", "zero", "zero")]["output_coordinates"],
            name=f"{point} zero output",
        )
        if zero.shape != (total_steps, 4):
            raise ValueError("zero record output shape does not match contract")
        drift_energy = float(np.square(np.linalg.norm(zero)))
        for column, channel in enumerate(channels):
            for shape, active in shapes.items():
                profile = np.zeros(total_steps, dtype=float)
                profile[: active.size] = active
                responses: dict[str, np.ndarray] = {}
                for sign, multiplier in (("positive", 1.0), ("negative", -1.0)):
                    row = indices[point][(channel, shape, sign)]
                    output = _finite_matrix(
                        row["output_coordinates"],
                        name=f"{point}/{channel}/{shape}/{sign} output",
                    )
                    if output.shape != (total_steps, 4):
                        raise ValueError("signed record output shape does not match contract")
                    physical = output - zero
                    inputs = (
                        multiplier
                        * profile[:, None]
                        * coordinate_map[:, column][None, :]
                    )
                    predicted = simulate_state_space(realizations[point], inputs)
                    metrics = _prediction_metrics(physical, predicted)
                    response_energy = float(np.square(np.linalg.norm(physical)))
                    signal_ratio = response_energy / max(drift_energy, 1.0e-24)
                    active_common_mean = float(np.mean(physical[: active.size, 0]))
                    sign_consistent = multiplier * active_common_mean < 0.0
                    metric_key = f"{point}/{channel}/{shape}/{sign}"
                    record_metrics[metric_key] = {
                        **metrics,
                        "signal_to_baseline_drift_energy_ratio": signal_ratio,
                        "common_frequency_sign_consistent": sign_consistent,
                    }
                    signal_pass = signal_pass and signal_ratio >= float(
                        thresholds["signal_to_baseline_drift_energy_ratio_minimum"]
                    )
                    sign_pass = sign_pass and sign_consistent
                    prediction_ok = (
                        metrics["total_nrmse"]
                        <= float(thresholds["total_nrmse_maximum"])
                        and metrics["peak_vector_residual"]
                        <= float(thresholds["peak_vector_residual_maximum"])
                    )
                    if point == development_point:
                        development_prediction_pass = (
                            development_prediction_pass and prediction_ok
                        )
                    else:
                        holdout_prediction_pass = holdout_prediction_pass and prediction_ok
                    responses[sign] = physical
                midpoint = 0.5 * (responses["positive"] + responses["negative"])
                denominator = 0.5 * (
                    np.linalg.norm(responses["positive"])
                    + np.linalg.norm(responses["negative"])
                )
                midpoint_ratio = (
                    float(np.linalg.norm(midpoint) / denominator)
                    if denominator > 0.0
                    else float("inf")
                )
                pair_key = f"{point}/{channel}/{shape}"
                pair_metrics[pair_key] = {
                    "normalized_l2_midpoint_residual": midpoint_ratio
                }
                pair_pass = pair_pass and midpoint_ratio <= float(
                    thresholds["pair_midpoint_nonlinearity_ratio_maximum"]
                )

    node_map = basis @ coordinate_map
    column_sum_errors = np.abs(np.sum(node_map, axis=0) + 1.0)
    conservation_pass = bool(
        np.all(
            column_sum_errors
            <= float(thresholds["node_power_sum_absolute_error_maximum"])
        )
    )
    singular_values = np.linalg.svd(node_map, compute_uv=False)
    rank = int(np.linalg.matrix_rank(node_map))
    singular_ratio = (
        float(singular_values[-1] / singular_values[0])
        if singular_values[0] > 0.0
        else 0.0
    )
    coverage_pass = rank == 4 and singular_ratio >= float(
        thresholds["singular_value_ratio_minimum"]
    )
    identification_guards = {
        "all_channels_observable": signal_pass,
        "all_common_frequency_signs_consistent": sign_pass,
        "all_registered_pairs_approximately_odd": pair_pass,
        "development_fit_within_envelope": development_prediction_pass,
        "untouched_holdout_within_envelope": holdout_prediction_pass,
        "active_power_conservation": conservation_pass,
        "full_rank_conditioned_coverage": coverage_pass,
    }

    if not all(validity_guards.values()):
        classification = "INVALID-PHYSICAL-DISTURBANCE-PACKAGE"
    elif not all(
        identification_guards[name]
        for name in (
            "all_channels_observable",
            "all_common_frequency_signs_consistent",
            "all_registered_pairs_approximately_odd",
            "development_fit_within_envelope",
            "untouched_holdout_within_envelope",
            "active_power_conservation",
        )
    ):
        classification = "BLOCK"
    elif not coverage_pass:
        classification = "QUALIFY"
    else:
        classification = "ALLOW"

    return {
        "schema_version": 1,
        "round": round_id,
        "question": question_id,
        "classification": classification,
        "validity_guards": validity_guards,
        "identification_guards": identification_guards,
        "record_metrics": record_metrics,
        "pair_metrics": pair_metrics,
        "package_metrics": {
            "coordinate_map": coordinate_map.tolist(),
            "node_map": node_map.tolist(),
            "node_column_sum_absolute_errors": column_sum_errors.tolist(),
            "rank": rank,
            "singular_values": singular_values.tolist(),
            "singular_value_ratio": singular_ratio,
        },
        "holdout_used_for_fitting": False,
        "scope": {
            "controller_executed": False,
            "closed_loop_executed": False,
            "distributed_runtime_executed": False,
            "training_executed": False,
            "eval_executed": False,
            "title_changed": False,
        },
    }
