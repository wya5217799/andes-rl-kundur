from __future__ import annotations

import pytest

from probes.r342_limited_reverse_decision import classify_r342


ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)


def _contrast(point: float, upper: float) -> dict[str, object]:
    return {
        endpoint: {
            "ratio_of_means_percent": {
                "point": point,
                "percentile_95_interval": [point - 1.0, upper],
            }
        }
        for endpoint in ENDPOINTS
    }


@pytest.mark.parametrize(
    ("overrides", "classification"),
    [
        ({"integrity_valid": False}, "INTEGRITY-INVALID"),
        ({"mechanism_engaged": False}, "NO-MECHANISM-ENGAGEMENT"),
        ({"controller_outcomes_complete": False}, "CONTROLLER-OUTCOME-FAILURE"),
        (
            {"candidate_vs_classical": _contrast(-1.9, -0.1)},
            "NO-CLASSICAL-INCREMENT",
        ),
        (
            {"candidate_vs_beta0": _contrast(-0.1, 0.01)},
            "NO-BETA-ZERO-INCREMENT",
        ),
        (
            {"positive_claim_guards": {"tail_sync": False}},
            "LIMITED-REVERSAL-GUARD-FAIL",
        ),
        ({}, "LIMITED-REVERSAL-INCREMENT"),
    ],
)
def test_r342_decision_tree(overrides: dict[str, object], classification: str) -> None:
    inputs: dict[str, object] = {
        "integrity_valid": True,
        "mechanism_engaged": True,
        "controller_outcomes_complete": True,
        "candidate_vs_classical": _contrast(-2.5, -0.1),
        "candidate_vs_beta0": _contrast(-0.5, -0.1),
        "candidate_vs_classical_seed_count": 3,
        "candidate_vs_beta0_seed_count": 3,
        "positive_claim_guards": {"tail_sync": True, "physical": True},
    }
    inputs.update(overrides)

    decision = classify_r342(**inputs)

    assert decision["classification"] == classification


def test_r342_success_requires_three_paired_seeds_for_each_comparison() -> None:
    decision = classify_r342(
        integrity_valid=True,
        mechanism_engaged=True,
        controller_outcomes_complete=True,
        candidate_vs_classical=_contrast(-2.5, -0.1),
        candidate_vs_beta0=_contrast(-0.5, -0.1),
        candidate_vs_classical_seed_count=3,
        candidate_vs_beta0_seed_count=2,
        positive_claim_guards={"tail_sync": True, "physical": True},
    )

    assert decision["classification"] == "NO-BETA-ZERO-INCREMENT"
