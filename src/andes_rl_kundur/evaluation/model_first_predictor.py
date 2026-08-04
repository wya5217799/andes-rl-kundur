"""Pure coupling-retaining pulse-response predictor for the model-first line.

The public seam fits only the sealed R312 signed-pair bank and predicts
finite-horizon frequency-coordinate increments.  It has no ANDES import and
does not authorize controller construction or training.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Literal

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    Stage1OperatingPoint,
    stage1_operating_points,
    stage1_power_coordinates,
    weighted_common_differential_transform,
)

TRAINING_ROUND = "R312"
TRAINING_QUESTION = "Q-0068"
TRAINING_AMPLITUDE_SYSTEM_PU = 0.05
TOTAL_STEPS = 25


def _finite_trace(values: object, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.shape != (TOTAL_STEPS, 4) or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be a finite 25-by-4 matrix")
    return array


def _coordinate_trace(
    record: Mapping[str, object],
    point: Stage1OperatingPoint,
) -> np.ndarray:
    rows = record.get("traces")
    if not isinstance(rows, list) or len(rows) != TOTAL_STEPS:
        raise ValueError("every training trace must contain exactly 25 rows")
    try:
        delta_frequency = _finite_trace(
            [row["delta_f_physical_hz"] for row in rows],
            name="delta_f_physical_hz",
        )
    except (KeyError, TypeError) as exc:
        raise ValueError("training trace is missing physical frequency") from exc
    transform = weighted_common_differential_transform(
        np.full(4, point.vsg_m_system)
    )
    omega_deviation = delta_frequency / 60.0
    return (transform.forward @ omega_deviation.T).T


def fit_coupling_retaining_predictor(
    records: Sequence[Mapping[str, object]],
    *,
    expected_round: str = TRAINING_ROUND,
    expected_question: str = TRAINING_QUESTION,
) -> dict[str, object]:
    """Fit the exact R312 central-difference trajectory templates.

    The result is JSON-serializable.  No held-out record, error metric, or
    validation outcome enters this function.
    """

    if len(records) != 27:
        raise ValueError("training bank must contain exactly 27 records")
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
    for record in records:
        if (
            record.get("round") != expected_round
            or record.get("question") != expected_question
        ):
            raise ValueError("training record identity mismatch")
        key = (
            str(record.get("operating_point", "")),
            str(record.get("coordinate", "")),
            str(record.get("sign", "")),
        )
        if key in keyed:
            raise ValueError(f"duplicate training record: {key}")
        keyed[key] = record
    if set(keyed) != expected_keys:
        raise ValueError("training bank key set does not match the frozen R312 bank")

    templates: dict[str, dict[str, object]] = {}
    for point_name, point in points.items():
        zero = _coordinate_trace(keyed[(point_name, "zero", "zero")], point)
        responses: dict[str, list[list[float]]] = {}
        for coordinate in coordinates:
            positive = _coordinate_trace(
                keyed[(point_name, coordinate, "positive")], point
            )
            negative = _coordinate_trace(
                keyed[(point_name, coordinate, "negative")], point
            )
            responses[coordinate] = (0.5 * (positive - negative)).tolist()
        templates[point_name] = {
            "zero_coordinate_trace": zero.tolist(),
            "responses": responses,
        }

    return {
        "schema_version": 1,
        "kind": "coupling-retaining-central-difference-trajectory-predictor",
        "training_round": expected_round,
        "training_question": expected_question,
        "training_trace_count": len(records),
        "training_amplitude_system_pu": TRAINING_AMPLITUDE_SYSTEM_PU,
        "horizon_steps": TOTAL_STEPS,
        "operating_points": [
            {
                "name": point.name,
                "vsg_m_device": point.vsg_m_device,
                "vsg_d_device": point.vsg_d_device,
                "tie_rx_scale": point.tie_rx_scale,
                "initial_soc": point.initial_soc,
            }
            for point in stage1_operating_points()
        ],
        "templates": templates,
        "full_arm": "retain-all-common-differential-output-blocks",
        "block_diagonal_arm": "zero-common-differential-cross-output-only",
        "controller_development_authorized": False,
        "training_authorized": False,
    }


def augment_predictor_with_development_point(
    base_model: Mapping[str, object],
    records: Sequence[Mapping[str, object]],
    *,
    point: Stage1OperatingPoint,
    development_round: str,
    development_question: str,
    amplitudes_system_pu: Sequence[float],
) -> dict[str, object]:
    """Append one equal-weight multi-amplitude unit-response template.

    Each signed pair is normalized back to the base model's 0.05-system-p.u.
    reference before averaging.  The function therefore adds operating-point
    information but no quadratic or outcome-selected amplitude term.
    """

    templates_value = base_model.get("templates")
    if not isinstance(templates_value, Mapping):
        raise ValueError("base model templates are missing")
    if point.name in templates_value:
        raise ValueError("development point already exists in the base model")
    amplitudes = tuple(float(value) for value in amplitudes_system_pu)
    amplitude_array = np.asarray(amplitudes, dtype=float)
    if (
        len(amplitudes) < 2
        or len(set(amplitudes)) != len(amplitudes)
        or not np.all(np.isfinite(amplitude_array))
        or np.any(amplitude_array <= 0.0)
    ):
        raise ValueError("development amplitudes must be distinct positive values")
    coordinates = tuple(stage1_power_coordinates())
    expected_keys = {
        ("zero", "zero", 0.0),
        *(
            (coordinate, sign, amplitude)
            for coordinate in coordinates
            for sign in ("positive", "negative")
            for amplitude in amplitudes
        ),
    }
    if len(records) != len(expected_keys):
        raise ValueError(
            f"development bank must contain exactly {len(expected_keys)} records"
        )
    keyed: dict[tuple[str, str, float], Mapping[str, object]] = {}
    for record in records:
        if (
            record.get("round") != development_round
            or record.get("question") != development_question
            or record.get("operating_point") != point.name
        ):
            raise ValueError("development record identity mismatch")
        key = (
            str(record.get("coordinate", "")),
            str(record.get("sign", "")),
            float(record.get("pulse_amplitude_system_pu", float("nan"))),
        )
        if key in keyed:
            raise ValueError(f"duplicate development record: {key}")
        keyed[key] = record
    if set(keyed) != expected_keys:
        raise ValueError("development bank key set does not match the frozen bank")

    zero = _coordinate_trace(keyed[("zero", "zero", 0.0)], point)
    reference_amplitude = float(base_model["training_amplitude_system_pu"])
    responses: dict[str, list[list[float]]] = {}
    for coordinate in coordinates:
        normalized_pairs: list[np.ndarray] = []
        for amplitude in amplitudes:
            positive = _coordinate_trace(
                keyed[(coordinate, "positive", amplitude)], point
            )
            negative = _coordinate_trace(
                keyed[(coordinate, "negative", amplitude)], point
            )
            normalized_pairs.append(
                0.5
                * (positive - negative)
                * (reference_amplitude / amplitude)
            )
        responses[coordinate] = np.mean(normalized_pairs, axis=0).tolist()

    model = deepcopy(dict(base_model))
    templates = model["templates"]
    if not isinstance(templates, dict):
        raise ValueError("copied base model templates are not mutable")
    templates[point.name] = {
        "zero_coordinate_trace": zero.tolist(),
        "responses": responses,
    }
    operating_points = model.get("operating_points")
    if not isinstance(operating_points, list):
        raise ValueError("base model operating points are missing")
    operating_points.append(
        {
            "name": point.name,
            "vsg_m_device": point.vsg_m_device,
            "vsg_d_device": point.vsg_d_device,
            "tie_rx_scale": point.tie_rx_scale,
            "initial_soc": point.initial_soc,
        }
    )
    model.update(
        {
            "kind": "coupling-retaining-local-simplex-trajectory-predictor",
            "training_rounds": [str(base_model["training_round"]), development_round],
            "training_questions": [
                str(base_model["training_question"]),
                development_question,
            ],
            "training_trace_count": int(base_model["training_trace_count"])
            + len(records),
            "development_point": point.name,
            "development_amplitudes_system_pu": list(amplitudes),
            "amplitude_model": "linear-equal-average-unit-response",
        }
    )
    return model


def _normalized_weights(
    weights: Mapping[str, float],
    point_names: set[str],
) -> dict[str, float]:
    if set(weights) != point_names:
        raise ValueError("weights must name every frozen training point exactly once")
    normalized = {name: float(value) for name, value in weights.items()}
    values = np.asarray(list(normalized.values()), dtype=float)
    if not np.all(np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("weights must be finite and nonnegative")
    if not np.isclose(np.sum(values), 1.0, rtol=0.0, atol=1e-12):
        raise ValueError("weights must sum to one")
    return normalized


def predict_coordinate_response(
    model: Mapping[str, object],
    *,
    weights: Mapping[str, float],
    coordinate: str,
    signed_amplitude_system_pu: float,
    arm: Literal["full", "block_diagonal"] = "full",
) -> np.ndarray:
    """Predict one 25-step forced coordinate response increment."""

    templates = model.get("templates")
    if not isinstance(templates, Mapping):
        raise ValueError("model templates are missing")
    if coordinate not in stage1_power_coordinates():
        raise ValueError("unknown predictor input coordinate")
    if arm not in {"full", "block_diagonal"}:
        raise ValueError("arm must be full or block_diagonal")
    amplitude = float(signed_amplitude_system_pu)
    if not np.isfinite(amplitude) or amplitude == 0.0:
        raise ValueError("signed amplitude must be finite and nonzero")
    point_weights = _normalized_weights(weights, set(templates))

    interpolated = np.zeros((TOTAL_STEPS, 4), dtype=float)
    for point_name, weight in point_weights.items():
        point_entry = templates[point_name]
        if not isinstance(point_entry, Mapping):
            raise ValueError("model point entry is invalid")
        responses = point_entry.get("responses")
        if not isinstance(responses, Mapping) or coordinate not in responses:
            raise ValueError("model response template is missing")
        interpolated += weight * _finite_trace(
            responses[coordinate], name=f"{point_name}/{coordinate}"
        )
    prediction = (
        amplitude / float(model["training_amplitude_system_pu"])
    ) * interpolated
    if arm == "block_diagonal":
        prediction = prediction.copy()
        if coordinate == "common":
            prediction[:, 1:] = 0.0
        else:
            prediction[:, 0] = 0.0
    return prediction


def response_error_metrics(
    actual_response: object,
    predicted_response: object,
    *,
    coordinate: str,
    sample_period_seconds: float,
) -> dict[str, float]:
    """Return total, peak, timing, and cross-block errors for one response."""

    actual = _finite_trace(actual_response, name="actual_response")
    predicted = _finite_trace(predicted_response, name="predicted_response")
    if coordinate not in stage1_power_coordinates():
        raise ValueError("unknown predictor input coordinate")
    sample_period = float(sample_period_seconds)
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")

    actual_norm = float(np.linalg.norm(actual))
    error = predicted - actual
    actual_magnitude = np.linalg.norm(actual, axis=1)
    predicted_magnitude = np.linalg.norm(predicted, axis=1)
    actual_peak = float(np.max(actual_magnitude))
    predicted_peak = float(np.max(predicted_magnitude))
    if coordinate == "common":
        actual_cross = actual[:, 1:]
        predicted_cross = predicted[:, 1:]
    else:
        actual_cross = actual[:, [0]]
        predicted_cross = predicted[:, [0]]
    cross_error = predicted_cross - actual_cross
    return {
        "total_nrmse": float(np.linalg.norm(error)) / max(actual_norm, 1e-15),
        "peak_magnitude_relative_error": abs(predicted_peak - actual_peak)
        / max(actual_peak, 1e-15),
        "peak_timing_error_seconds": abs(
            int(np.argmax(predicted_magnitude)) - int(np.argmax(actual_magnitude))
        )
        * sample_period,
        "cross_actual_l2": float(np.linalg.norm(actual_cross)),
        "cross_error_l2": float(np.linalg.norm(cross_error)),
    }
