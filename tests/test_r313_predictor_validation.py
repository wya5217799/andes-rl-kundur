from __future__ import annotations

import pytest

from probes.r313_predictor_validation import (
    aggregate_cross_value,
    classify_predictor_validation,
)


THRESHOLDS = {
    "total_nrmse_max": 0.15,
    "peak_magnitude_relative_error_max": 0.10,
    "peak_timing_error_seconds_max": 0.2,
    "aggregate_cross_squared_error_reduction_min": 0.20,
    "cross_record_win_fraction_min": 0.75,
}


def test_cross_value_uses_the_matched_block_arm_as_the_counterfactual() -> None:
    summary = aggregate_cross_value(
        full_cross_errors=[1.0, 2.0, 1.0, 2.0],
        block_cross_errors=[2.0, 2.0, 2.0, 2.0],
    )

    assert summary["aggregate_cross_squared_error_reduction"] == pytest.approx(
        0.375
    )
    assert summary["cross_record_win_fraction"] == pytest.approx(0.5)
    assert summary["cross_signal_observable"] is True


def test_classification_fails_closed_before_interpreting_predictor_metrics() -> None:
    result = classify_predictor_validation(
        execution_valid=False,
        eval_valid=True,
        metric_summary=None,
        thresholds=THRESHOLDS,
    )

    assert result["classification"] == "INVALID-PREDICTOR-VALIDATION"
    assert result["metric_guards"] is None


def test_classification_passes_only_when_every_frozen_metric_guard_passes() -> None:
    passing = {
        "max_total_nrmse": 0.14,
        "max_peak_magnitude_relative_error": 0.09,
        "max_peak_timing_error_seconds": 0.2,
        "aggregate_cross_squared_error_reduction": 0.21,
        "cross_record_win_fraction": 0.75,
        "cross_signal_observable": True,
    }
    result = classify_predictor_validation(
        execution_valid=True,
        eval_valid=True,
        metric_summary=passing,
        thresholds=THRESHOLDS,
    )
    assert result["classification"] == "PREDICTOR-PASS"
    assert all(result["metric_guards"].values())

    failing = dict(passing, max_total_nrmse=0.1500001)
    result = classify_predictor_validation(
        execution_valid=True,
        eval_valid=True,
        metric_summary=failing,
        thresholds=THRESHOLDS,
    )
    assert result["classification"] == "PREDICTOR-NO-GO"
    assert result["metric_guards"]["total_nrmse"] is False
