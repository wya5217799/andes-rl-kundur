"""Behavior tests for the bounded outcome-seeing headroom witness."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.bounded_headroom_witness import (
    build_contract,
    classify_headroom,
    derive_residual_schedule,
    select_disturbance_candidate,
    select_probe_pair,
)


def _parent_record() -> dict[str, object]:
    return {
        "steps": [
            {"freq_hz_physical": [61.0, 59.0, 60.0, 60.0]},
            {"freq_hz_physical": [62.0, 58.0, 60.0, 60.0]},
            {"freq_hz_physical": [63.0, 57.0, 60.0, 60.0]},
        ]
    }


def _summary(
    *,
    differential_energy: float,
    settling: float,
    offdiag: float,
    cross_ratio: float,
    common_iae: float = 1.0,
    peak: float = 1.0,
    rocof: float = 1.0,
) -> dict[str, object]:
    return {
        "disturbance": {
            "mean_differential_frequency_energy_hz2_s": differential_energy,
            "mean_differential_settling_seconds": settling,
            "mean_common_frequency_iae_hz_s": common_iae,
            "mean_worst_device_peak_abs_hz": peak,
            "mean_max_rocof_hz_per_s": rocof,
        },
        "probe": {
            "diagonal_response_energy_hz2_s": 10.0,
            "off_diagonal_response_energy_hz2_s": offdiag,
            "off_diagonal_to_diagonal_energy_ratio": cross_ratio,
        },
    }


def test_contract_freezes_four_candidates_and_forty_new_records() -> None:
    contract = build_contract()

    assert contract["lead_steps"] == 2
    assert contract["candidate_record_count"] == 40
    assert [row["candidate_id"] for row in contract["candidate_specs"]] == [
        "amp0p25_polneg",
        "amp0p25_polpos",
        "amp0p50_polneg",
        "amp0p50_polpos",
    ]
    assert contract["training_authorized"] is False


def test_schedule_is_future_shifted_zero_sum_and_globally_normalized() -> None:
    schedule = derive_residual_schedule(
        _parent_record(),
        amplitude=0.5,
        polarity=1.0,
        lead_steps=1,
    )

    np.testing.assert_allclose(
        schedule,
        [
            [-1.0 / 3.0, 1.0 / 3.0, 0.0, 0.0],
            [-0.5, 0.5, 0.0, 0.0],
            [-0.5, 0.5, 0.0, 0.0],
        ],
    )
    np.testing.assert_allclose(np.sum(schedule, axis=1), 0.0, atol=1.0e-15)


def test_headroom_pass_requires_both_disturbance_and_probe_improvement() -> None:
    baseline = _summary(
        differential_energy=100.0,
        settling=2.0,
        offdiag=20.0,
        cross_ratio=2.0,
    )
    oracle = _summary(
        differential_energy=94.0,
        settling=2.0,
        offdiag=18.0,
        cross_ratio=1.8,
        common_iae=1.04,
        peak=1.09,
        rocof=1.09,
    )

    decision = classify_headroom(
        baseline,
        oracle,
        all_candidate_records_valid=True,
    )

    assert decision["classification"] == "BOUNDED-HEADROOM-WITNESS-PASS"
    assert decision["training_authorized"] is False
    assert decision["checks"] == {
        "complete_valid_candidate_bank": True,
        "disturbance_energy_headroom": True,
        "settling_no_harm": True,
        "probe_absolute_cross_headroom": True,
        "probe_normalized_cross_headroom": True,
        "common_frequency_no_harm": True,
        "peak_no_harm": True,
        "rocof_no_harm": True,
    }


def test_headroom_stops_when_only_disturbance_endpoint_improves() -> None:
    baseline = _summary(
        differential_energy=100.0,
        settling=2.0,
        offdiag=20.0,
        cross_ratio=2.0,
    )
    oracle = _summary(
        differential_energy=90.0,
        settling=2.0,
        offdiag=19.5,
        cross_ratio=1.95,
    )

    decision = classify_headroom(
        baseline,
        oracle,
        all_candidate_records_valid=True,
    )

    assert decision["classification"] == "STOP-NO-DETECTED-JOINT-HEADROOM"
    assert decision["checks"]["disturbance_energy_headroom"] is True
    assert decision["checks"]["probe_absolute_cross_headroom"] is False


def test_invalid_candidate_bank_precedes_performance_classification() -> None:
    baseline = _summary(
        differential_energy=100.0,
        settling=2.0,
        offdiag=20.0,
        cross_ratio=2.0,
    )
    oracle = _summary(
        differential_energy=80.0,
        settling=1.0,
        offdiag=10.0,
        cross_ratio=1.0,
    )

    decision = classify_headroom(
        baseline,
        oracle,
        all_candidate_records_valid=False,
    )

    assert decision["classification"] == "ANALYSIS-INVALID"
    assert decision["training_authorized"] is False


def test_disturbance_selector_uses_best_no_harm_candidate_or_baseline() -> None:
    baseline = {
        "candidate_id": "baseline_fallback",
        "differential_frequency_energy_hz2_s": 10.0,
        "eligible": True,
    }
    candidates = [
        {
            "candidate_id": "lower_but_harmful",
            "differential_frequency_energy_hz2_s": 7.0,
            "eligible": False,
        },
        {
            "candidate_id": "best_valid",
            "differential_frequency_energy_hz2_s": 8.0,
            "eligible": True,
        },
        {
            "candidate_id": "valid_but_worse",
            "differential_frequency_energy_hz2_s": 9.0,
            "eligible": True,
        },
    ]

    selected = select_disturbance_candidate(baseline, candidates)
    fallback = select_disturbance_candidate(
        baseline,
        [{**candidates[0]}],
    )

    assert selected["candidate_id"] == "best_valid"
    assert fallback["candidate_id"] == "baseline_fallback"


def test_probe_selector_enforces_diagonal_response_floor_before_cross_minimum() -> None:
    baseline = {
        "pair_id": "baseline_fallback",
        "diagonal_response_energy_hz2_s": 10.0,
        "off_diagonal_response_energy_hz2_s": 2.0,
        "off_diagonal_to_diagonal_energy_ratio": 0.2,
    }
    pairs = [
        {
            "pair_id": "collapsed_response",
            "diagonal_response_energy_hz2_s": 8.0,
            "off_diagonal_response_energy_hz2_s": 0.5,
            "off_diagonal_to_diagonal_energy_ratio": 0.0625,
        },
        {
            "pair_id": "valid_decoupling",
            "diagonal_response_energy_hz2_s": 9.5,
            "off_diagonal_response_energy_hz2_s": 1.5,
            "off_diagonal_to_diagonal_energy_ratio": 1.5 / 9.5,
        },
    ]

    selected = select_probe_pair(
        baseline,
        pairs,
        diagonal_floor_ratio=0.90,
    )

    assert selected["pair_id"] == "valid_decoupling"
