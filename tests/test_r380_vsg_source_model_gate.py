from __future__ import annotations

import numpy as np
from probes.r380_vsg_source_model_gate import (
    analyse_validation_records,
    classify_r380,
    input_sequence,
    record_specs,
)

from andes_rl_kundur.evaluation.model_first_input_bridge import (
    SampledInputModel,
)


def test_r380_bank_has_two_points_and_eighteen_frozen_records_per_point() -> None:
    specs = record_specs()

    assert len(specs) == 36
    for point in ("P0", "P1"):
        point_specs = [row for row in specs if row["point"] == point]
        assert len(point_specs) == 18
        assert [row["kind"] for row in point_specs].count("zero") == 2
        assert [row["kind"] for row in point_specs].count("control") == 8
        assert [row["kind"] for row in point_specs].count("load") == 6
        assert [row["kind"] for row in point_specs].count("combined") == 2
    nonzero = next(row for row in specs if row["kind"] == "control")
    sequence = input_sequence(nonzero)
    assert sequence.shape == (125, 7)
    np.testing.assert_allclose(sequence[:5], 0.0)
    assert np.count_nonzero(sequence[5:10]) == 5
    np.testing.assert_allclose(sequence[10:], 0.0)


def test_r380_classifier_preserves_invalid_stop_qualify_and_allow() -> None:
    passing_control = [{"kind": "control", "pass": True}]
    passing_all = passing_control + [
        {"kind": "load", "pass": True},
        {"kind": "combined", "pass": True},
    ]

    assert (
        classify_r380(validity_pass=False, construction_pass=True, metrics=passing_all)
        == "INVALID-OBJECT-OR-PORT"
    )
    assert (
        classify_r380(validity_pass=True, construction_pass=False, metrics=[])
        == "STOP-SOURCE-MODEL"
    )
    assert (
        classify_r380(
            validity_pass=True,
            construction_pass=True,
            metrics=[{"kind": "control", "pass": False}],
        )
        == "STOP-MODEL-FIDELITY"
    )
    assert (
        classify_r380(
            validity_pass=True,
            construction_pass=True,
            metrics=passing_control + [{"kind": "load", "pass": False}],
        )
        == "QUALIFY-DIAGNOSTIC-ONLY"
    )
    assert (
        classify_r380(validity_pass=True, construction_pass=True, metrics=passing_all)
        == "ALLOW-MODEL-BASED-DESIGN"
    )


def test_r380_analysis_compares_each_record_to_its_first_zero_repeat() -> None:
    models = {
        point: SampledInputModel(
            state_matrix=np.zeros((4, 4)),
            input_matrix=np.zeros((4, 7)),
            output_matrix=np.eye(4),
            feedthrough_matrix=np.asarray(
                [
                    [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0],
                    [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
                ]
            ),
        )
        for point in ("P0", "P1")
    }
    records = []
    zero_bias = np.full((125, 4), 1.0e-10)
    for spec in record_specs():
        if spec["kind"] == "zero":
            output = zero_bias.copy()
        else:
            sequence = input_sequence(spec)
            output = zero_bias + sequence @ models[spec["point"]].feedthrough_matrix.T
        records.append(
            {
                "record_id": spec["record_id"],
                "point": spec["point"],
                "kind": spec["kind"],
                "frequency_deviation_hz": output.tolist(),
                "guards": {"synthetic": True},
            }
        )

    analysis = analyse_validation_records(
        models=models,
        records=records,
        construction_pass=True,
    )

    assert analysis["classification"] == "ALLOW-MODEL-BASED-DESIGN"
    assert analysis["validity_pass"]
    assert len(analysis["record_metrics"]) == 32
    assert max(row["nrmse"] for row in analysis["record_metrics"].values()) == 0.0
