from __future__ import annotations

import pytest

from andes_rl_kundur.evaluation.u4_guard_audit import phase_i_residuals


def _summary(scale: float = 1.0) -> dict[str, object]:
    return {
        "disturbance_differential_energy": 2.0 * scale,
        "off_diagonal_response_energy": 3.0 * scale,
        "common_frequency_iae_hz_s": 4.0 * scale,
        "worst_unit_peak_hz": 5.0 * scale,
        "worst_rocof_hz_s": 6.0 * scale,
        "action_rms": 7.0 * scale,
        "action_total_variation": 8.0 * scale,
        "action_saturation_fraction": 0.01 * scale,
        "valid": True,
        "actuator_mapping_pass": True,
        "action_bound_violation": False,
        "action_slew_violation": False,
    }


def test_phase_i_thresholds_are_zero_at_exact_limits() -> None:
    static = _summary()
    candidate = _summary()
    candidate.update(
        {
            "disturbance_differential_energy": 1.9,
            "off_diagonal_response_energy": 2.85,
            "common_frequency_iae_hz_s": 4.12,
            "worst_unit_peak_hz": 5.15,
            "worst_rocof_hz_s": 6.18,
            "action_rms": 7.7,
            "action_total_variation": 8.8,
            "action_saturation_fraction": 0.05,
        }
    )
    assert max(abs(value) for value in phase_i_residuals(candidate, static).values()) < 1e-12


def test_invalid_candidate_receives_positive_infinity() -> None:
    candidate = _summary(0.5)
    candidate["valid"] = False
    assert phase_i_residuals(candidate, _summary())["validity"] == float("inf")


def test_zero_static_denominator_is_rejected() -> None:
    static = _summary()
    static["action_rms"] = 0.0
    with pytest.raises(ValueError, match="denominator"):
        phase_i_residuals(_summary(), static)
