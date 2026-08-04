from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pytest

from andes_rl_kundur.env.andes.model_first_contract import (
    Stage1OperatingPoint,
    stage1_operating_points,
    weighted_common_differential_transform,
)
from andes_rl_kundur.evaluation.model_first_predictor import (
    augment_predictor_with_development_point,
    fit_coupling_retaining_predictor,
    predict_coordinate_response,
    response_error_metrics,
)


def _record(
    point: Stage1OperatingPoint,
    coordinate: str,
    sign: str,
    coordinate_trace: np.ndarray,
) -> dict[str, object]:
    transform = weighted_common_differential_transform(
        np.full(4, point.vsg_m_system)
    )
    omega = (transform.inverse @ coordinate_trace.T).T
    delta_f = 60.0 * omega
    return {
        "round": "R312",
        "question": "Q-0068",
        "operating_point": point.name,
        "coordinate": coordinate,
        "sign": sign,
        "traces": [
            {"delta_f_physical_hz": row.tolist()} for row in delta_f
        ],
    }


def _training_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    coordinates = ("common", "edge_0", "edge_1", "edge_2")
    point_scales = {"OP0": 1.0, "OP1": 2.0, "OP2": 3.0}
    time = np.linspace(0.0, 1.0, 25)
    for point in stage1_operating_points():
        zero = np.zeros((25, 4))
        records.append(_record(point, "zero", "zero", zero))
        for coordinate_index, coordinate in enumerate(coordinates, start=1):
            endpoint = point_scales[point.name] * coordinate_index * np.array(
                [1.0, 0.1, 0.2, 0.3]
            )
            response = time[:, None] * endpoint[None, :]
            records.append(_record(point, coordinate, "positive", response))
            records.append(_record(point, coordinate, "negative", -response))
    return records


def test_predictor_fits_r312_pairs_and_interpolates_unseen_amplitude() -> None:
    model = fit_coupling_retaining_predictor(_training_records())

    assert model["training_round"] == "R312"
    assert model["training_question"] == "Q-0068"
    assert model["training_trace_count"] == 27
    assert model["training_amplitude_system_pu"] == 0.05
    assert model["operating_points"] == [
        asdict(point) for point in stage1_operating_points()
    ]

    prediction = predict_coordinate_response(
        model,
        weights={"OP0": 0.50, "OP1": 0.25, "OP2": 0.25},
        coordinate="common",
        signed_amplitude_system_pu=0.025,
        arm="full",
    )

    assert prediction.shape == (25, 4)
    assert prediction[-1].tolist() == pytest.approx(
        [0.875, 0.0875, 0.175, 0.2625]
    )


def test_block_ablation_changes_only_common_differential_cross_output() -> None:
    model = fit_coupling_retaining_predictor(_training_records())
    weights = {"OP0": 0.50, "OP1": 0.25, "OP2": 0.25}

    full_common = predict_coordinate_response(
        model,
        weights=weights,
        coordinate="common",
        signed_amplitude_system_pu=-0.065,
        arm="full",
    )
    block_common = predict_coordinate_response(
        model,
        weights=weights,
        coordinate="common",
        signed_amplitude_system_pu=-0.065,
        arm="block_diagonal",
    )
    assert block_common[:, 0].tolist() == pytest.approx(full_common[:, 0])
    assert np.count_nonzero(block_common[:, 1:]) == 0

    full_edge = predict_coordinate_response(
        model,
        weights=weights,
        coordinate="edge_1",
        signed_amplitude_system_pu=0.065,
        arm="full",
    )
    block_edge = predict_coordinate_response(
        model,
        weights=weights,
        coordinate="edge_1",
        signed_amplitude_system_pu=0.065,
        arm="block_diagonal",
    )
    assert block_edge[:, 1:].tolist() == pytest.approx(full_edge[:, 1:])
    assert np.count_nonzero(block_edge[:, 0]) == 0


def test_predictor_fails_closed_when_the_r312_training_bank_is_incomplete() -> None:
    with pytest.raises(ValueError, match="exactly 27"):
        fit_coupling_retaining_predictor(_training_records()[:-1])


def test_response_metrics_use_independent_actual_response() -> None:
    actual = np.zeros((25, 4))
    actual[10, 0] = 2.0
    actual[11, 1] = 1.0
    predicted = 0.9 * actual

    metrics = response_error_metrics(
        actual,
        predicted,
        coordinate="common",
        sample_period_seconds=0.2,
    )

    assert metrics["total_nrmse"] == pytest.approx(0.1)
    assert metrics["peak_magnitude_relative_error"] == pytest.approx(0.1)
    assert metrics["peak_timing_error_seconds"] == pytest.approx(0.0)
    assert metrics["cross_actual_l2"] == pytest.approx(1.0)
    assert metrics["cross_error_l2"] == pytest.approx(0.1)


def test_predictor_adds_one_multiamplitude_development_point_without_quadratic_fit() -> None:
    base_model = fit_coupling_retaining_predictor(_training_records())
    point = Stage1OperatingPoint("HP1", 180.0, 90.0, 1.2, 0.42)
    time = np.linspace(0.0, 1.0, 25)
    records: list[dict[str, object]] = [
        _record(point, "zero", "zero", np.zeros((25, 4)))
    ]
    records[0]["round"] = "R313"
    records[0]["question"] = "Q-0069"
    records[0]["pulse_amplitude_system_pu"] = 0.0
    for coordinate_index, coordinate in enumerate(
        ("common", "edge_0", "edge_1", "edge_2"), start=1
    ):
        unit_endpoint = 4.0 * coordinate_index * np.array([1.0, 0.1, 0.2, 0.3])
        for amplitude in (0.025, 0.065):
            response = (
                amplitude / 0.05
            ) * time[:, None] * unit_endpoint[None, :]
            for sign, values in (("positive", response), ("negative", -response)):
                record = _record(point, coordinate, sign, values)
                record["round"] = "R313"
                record["question"] = "Q-0069"
                record["pulse_amplitude_system_pu"] = amplitude
                records.append(record)

    model = augment_predictor_with_development_point(
        base_model,
        records,
        point=point,
        development_round="R313",
        development_question="Q-0069",
        amplitudes_system_pu=(0.025, 0.065),
    )

    assert model["training_rounds"] == ["R312", "R313"]
    assert model["training_trace_count"] == 44
    assert model["amplitude_model"] == "linear-equal-average-unit-response"
    prediction = predict_coordinate_response(
        model,
        weights={"OP0": 0.2, "OP1": 0.3, "OP2": 0.0, "HP1": 0.5},
        coordinate="common",
        signed_amplitude_system_pu=0.025,
        arm="full",
    )
    assert prediction[-1].tolist() == pytest.approx(
        [1.4, 0.14, 0.28, 0.42]
    )
