"""Slice-4 tests: R405 contract and pre-registered decision tree.

Expected values come from the frozen plan text and the sealed R402 sidecars,
never from re-running the implementation formulas.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

from andes_rl_kundur.evaluation.r405_homogenization_gate import (  # noqa: E402
    classify_r405,
    build_contract,
    contract_sha256,
)


def test_contract_builds_closed_and_frozen():
    c = build_contract()
    assert c["round"] == "R405"
    assert c["manuscript_line"] == "yang-md-decoupling-marl"
    assert len(c["profiles"]) == 8
    assert len(c["scenario_ids"]) == 48
    assert c["arms"] == [
        "zero_action",
        "local_neighbour_md_km2_kd2",
        "candidate_a_homogenized",
    ]
    t = c["thresholds"]
    assert t["cross_ratio"] == 0.95
    assert t["differential_ratio"] == 0.95
    assert t["common_no_harm"] == 1.03
    assert t["action_stress"] == 1.10
    assert t["saturation_fraction"] == 0.0
    assert c["training_authorized"] is False


def test_contract_binds_sealed_reference_sidecar():
    c = build_contract()
    ref = c["reference"]
    assert ref["source"] == "results/research_loop/r402_cd_matd3_canary/endpoint_table.json"
    path = ROOT / ref["source"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert ref["sha256"] == digest
    # Sealed aggregate endpoints copied verbatim (spot-check both).
    agg = ref["deterministic_aggregate"]
    assert agg["off_diagonal_response_energy"] == pytest.approx(
        0.00034260449381761277, rel=1e-12
    )
    assert agg["disturbance_differential_energy"] == pytest.approx(
        0.0022148944818784584, rel=1e-12
    )
    assert set(ref["profile_summaries"]) == {
        "canary_eval_a", "canary_eval_b", "canary_eval_c", "canary_eval_d",
    }


def test_contract_sha256_stable():
    c = build_contract()
    assert contract_sha256(c) == contract_sha256(build_contract())


def _payload(validity=True, guards=True, cross=0.8, diff=0.9):
    return {
        "validity": {
            "sealed_match_ok": validity,
            "complete": validity,
            "all_rows_valid": validity,
        },
        "endpoints": {
            "cross_ratio": cross,
            "differential_ratio": diff,
            "cross_ratio_eval_only": cross,
            "differential_ratio_eval_only": diff,
        },
        "guards": {
            "common_no_harm_ok": guards,
            "stress_ok": guards,
            "saturation_ok": guards,
            "completion_ok": guards,
        },
    }


def test_classifier_pass_a():
    out = classify_r405(_payload(cross=0.8, diff=0.9))
    assert out["classification"] == "PASS-A"


def test_classifier_partial_a_when_differential_fails():
    out = classify_r405(_payload(cross=0.8, diff=1.05))
    assert out["classification"] == "PARTIAL-A"


def test_classifier_no_cross_effect_dominates_partial():
    out = classify_r405(_payload(cross=0.96, diff=1.05))
    assert out["classification"] == "NO-CROSS-EFFECT"


def test_classifier_guard_fail_dominates_endpoints():
    out = classify_r405(_payload(guards=False, cross=0.8, diff=0.9))
    assert out["classification"] == "GUARD-FAIL"


def test_classifier_invalid_dominates_everything():
    out = classify_r405(_payload(validity=False, guards=False, cross=0.8, diff=0.9))
    assert out["classification"] == "INVALID"


def test_classifier_boundary_at_threshold_passes():
    out = classify_r405(_payload(cross=0.95, diff=0.95))
    assert out["classification"] == "PASS-A"