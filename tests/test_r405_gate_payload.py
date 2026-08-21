"""Slice-6 tests: gate payload aggregation from per-profile summaries.

Expected ratios are hand-computed from synthetic two-profile summaries; the
sealed-reference reproduction check uses perturbed values.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


from andes_rl_kundur.evaluation.r405_homogenization_gate import (  # noqa: E402
    CANDIDATE_ARM,
    REFERENCE_ARM,
    SUMMARY_KEYS,
    build_contract,
    classify_r405,
    compute_gate_payload,
)

def _summary(off, diff, iae, peak, rocof, rms, tv):
    return {
        "off_diagonal_response_energy": off,
        "disturbance_differential_energy": diff,
        "common_frequency_iae_hz_s": iae,
        "worst_unit_peak_hz": peak,
        "worst_rocof_hz_s": rocof,
        "action_rms": rms,
        "action_total_variation": tv,
        "action_saturation_fraction": 0.0,
        "valid": True,
        "record_count": 6,
    }


def _summaries(cross_off=0.4, cross_diff=0.5):
    c = build_contract()
    out = {REFERENCE_ARM: {}, CANDIDATE_ARM: {}}
    for p in c["profiles"]:
        pid = str(p["profile_id"])
        if p["split"] == "evaluation":
            sealed = c["reference"]["profile_summaries"][pid]
            # Sealed profile summaries carry the five guard metrics; the two
            # endpoint energies are aggregate-level (off=3.426e-4, diff=2.215e-3
            # across the four evaluation profiles).
            out[REFERENCE_ARM][pid] = _summary(
                3.4260449381761277e-4 / 4.0,
                2.2148944818784584e-3 / 4.0,
                sealed["common_frequency_iae_hz_s"],
                sealed["worst_unit_peak_hz"],
                sealed["worst_rocof_hz_s"],
                sealed["action_rms"],
                sealed["action_total_variation"],
            )
        else:
            out[REFERENCE_ARM][pid] = _summary(0.001, 0.002, 1.0, 0.05, 0.1, 0.1, 1.0)
        ref = out[REFERENCE_ARM][pid]
        # Candidate A scales the SAME profile's reference values, so the
        # aggregate ratio equals the per-profile factor exactly.
        out[CANDIDATE_ARM][pid] = _summary(
            cross_off * ref["off_diagonal_response_energy"],
            cross_diff * ref["disturbance_differential_energy"],
            ref["common_frequency_iae_hz_s"],
            ref["worst_unit_peak_hz"],
            ref["worst_rocof_hz_s"],
            ref["action_rms"],
            ref["action_total_variation"],
        )
    return out


def test_payload_ratios_hand_computed():
    s = _summaries(cross_off=0.4, cross_diff=0.5)
    payload = compute_gate_payload(s)
    assert payload["validity"]["sealed_match_ok"] is True
    assert payload["endpoints"]["cross_ratio"] == pytest.approx(0.4, rel=1e-12)
    assert payload["endpoints"]["differential_ratio"] == pytest.approx(0.5, rel=1e-12)
    assert payload["guards"]["common_no_harm_ok"] is True
    assert payload["guards"]["stress_ok"] is True
    assert payload["guards"]["saturation_ok"] is True
    assert payload["guards"]["completion_ok"] is True
    assert classify_r405(payload)["classification"] == "PASS-A"


def test_payload_guard_ratios_hand_computed():
    s = _summaries(cross_off=0.4, cross_diff=0.5)
    c = build_contract()
    # Make candidate A 2x on common IAE, peak, RoCoF, action RMS and TV.
    for pid in s[CANDIDATE_ARM]:
        for key in (
            "common_frequency_iae_hz_s",
            "worst_unit_peak_hz",
            "worst_rocof_hz_s",
            "action_rms",
            "action_total_variation",
        ):
            s[CANDIDATE_ARM][pid][key] = 2.0 * s[REFERENCE_ARM][pid][key]
    payload = compute_gate_payload(s)
    g = payload["guard_ratios"]
    assert g["common_iae"] == pytest.approx(2.0, rel=1e-9)
    assert g["worst_peak"] == pytest.approx(2.0, rel=1e-9)
    assert g["worst_rocof"] == pytest.approx(2.0, rel=1e-9)
    assert g["action_rms"] == pytest.approx(2.0, rel=1e-9)
    assert g["action_total_variation"] == pytest.approx(2.0, rel=1e-9)
    assert payload["guards"]["common_no_harm_ok"] is False
    assert payload["guards"]["stress_ok"] is False
    assert classify_r405(payload)["classification"] == "GUARD-FAIL"


def test_payload_sealed_mismatch_is_invalid():
    s = _summaries()
    c = build_contract()
    eval_pid = next(
        str(p["profile_id"]) for p in c["profiles"] if p["split"] == "evaluation"
    )
    s[REFERENCE_ARM][eval_pid]["common_frequency_iae_hz_s"] *= 1.5
    payload = compute_gate_payload(s)
    assert payload["validity"]["sealed_match_ok"] is False
    assert classify_r405(payload)["classification"] == "INVALID"


def test_payload_cross_above_threshold_no_cross_effect():
    s = _summaries(cross_off=0.98, cross_diff=0.5)
    payload = compute_gate_payload(s)
    assert classify_r405(payload)["classification"] == "NO-CROSS-EFFECT"


def test_payload_partial_when_differential_fails():
    s = _summaries(cross_off=0.4, cross_diff=1.2)
    payload = compute_gate_payload(s)
    assert classify_r405(payload)["classification"] == "PARTIAL-A"