from probes.r315_dynamic_reduction_validation import classify_dynamic_reduction


THRESHOLDS = {
    "parent_physical_total_nrmse_max": 0.15,
    "reduced_parent_total_nrmse_max": 0.10,
    "reduced_physical_total_nrmse_max": 0.15,
    "maximum_normalized_absolute_residual_max": 0.20,
    "peak_magnitude_relative_error_max": 0.10,
    "peak_timing_error_seconds_max": 0.2,
    "aggregate_cross_squared_error_reduction_min": 0.20,
    "cross_record_win_fraction_min": 0.75,
    "maximum_spectral_radius": 0.995,
}


def test_dynamic_reduction_classifier_fails_closed_then_passes_every_gate() -> None:
    invalid = classify_dynamic_reduction(
        execution_valid=False,
        eval_valid=True,
        metric_summary=None,
        thresholds=THRESHOLDS,
    )
    assert invalid["classification"] == "INVALID-DYNAMIC-REDUCTION-VALIDATION"

    passing = classify_dynamic_reduction(
        execution_valid=True,
        eval_valid=True,
        metric_summary={
            "max_parent_physical_total_nrmse": 0.14,
            "max_reduced_parent_total_nrmse": 0.09,
            "max_reduced_physical_total_nrmse": 0.14,
            "max_normalized_absolute_residual": 0.19,
            "max_peak_magnitude_relative_error": 0.09,
            "max_peak_timing_error_seconds": 0.2,
            "aggregate_cross_squared_error_reduction": 0.21,
            "cross_record_win_fraction": 0.75,
            "cross_signal_observable": True,
            "maximum_spectral_radius": 0.995,
        },
        thresholds=THRESHOLDS,
    )
    assert passing["classification"] == "DYNAMIC-REDUCTION-PASS"
    assert all(passing["metric_guards"].values())
