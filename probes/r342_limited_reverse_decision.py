"""Prospectively frozen R342 limited-reversal decision tree."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PRIMARY_ENDPOINTS = (
    "normalized_sync_loss_hz2",
    "fast_inter_area_iae_hz_s",
)


def _effect(contrast: Mapping[str, Any], endpoint: str) -> Mapping[str, Any]:
    return contrast[endpoint]["ratio_of_means_percent"]


def _material_vs_classical(contrast: Mapping[str, Any]) -> bool:
    return all(
        float(_effect(contrast, endpoint)["point"]) <= -2.0
        and float(_effect(contrast, endpoint)["percentile_95_interval"][1]) < 0.0
        for endpoint in PRIMARY_ENDPOINTS
    )


def _strict_vs_beta_zero(contrast: Mapping[str, Any]) -> bool:
    return all(
        float(_effect(contrast, endpoint)["point"]) < 0.0
        and float(_effect(contrast, endpoint)["percentile_95_interval"][1]) < 0.0
        for endpoint in PRIMARY_ENDPOINTS
    )


def classify_r342(
    *,
    integrity_valid: bool,
    mechanism_engaged: bool,
    controller_outcomes_complete: bool,
    candidate_vs_classical: Mapping[str, Any],
    candidate_vs_beta0: Mapping[str, Any],
    candidate_vs_classical_seed_count: int,
    candidate_vs_beta0_seed_count: int,
    positive_claim_guards: Mapping[str, bool],
) -> dict[str, Any]:
    """Apply the frozen causal-efficacy-guard order once."""

    classical_gate = bool(
        _material_vs_classical(candidate_vs_classical)
        and candidate_vs_classical_seed_count >= 3
    )
    beta_zero_gate = bool(
        _strict_vs_beta_zero(candidate_vs_beta0)
        and candidate_vs_beta0_seed_count >= 3
    )
    guards_pass = bool(positive_claim_guards) and all(
        positive_claim_guards.values()
    )
    gates = {
        "integrity_valid": bool(integrity_valid),
        "mechanism_engaged": bool(mechanism_engaged),
        "controller_outcomes_complete": bool(controller_outcomes_complete),
        "candidate_vs_classical_both_primary": classical_gate,
        "candidate_vs_beta0_both_primary": beta_zero_gate,
        "candidate_vs_classical_seed_count": int(
            candidate_vs_classical_seed_count
        ),
        "candidate_vs_beta0_seed_count": int(candidate_vs_beta0_seed_count),
        "positive_claim_guards_pass": guards_pass,
    }
    if not integrity_valid:
        classification = "INTEGRITY-INVALID"
        reason = "sealing, provenance, budget, action, or statistical integrity failed"
    elif not mechanism_engaged:
        classification = "NO-MECHANISM-ENGAGEMENT"
        reason = "the beta-0.1 policies never executed a reverse aligned command"
    elif not controller_outcomes_complete:
        classification = "CONTROLLER-OUTCOME-FAILURE"
        reason = "one or more retained controller outcomes did not complete"
    elif not classical_gate:
        classification = "NO-CLASSICAL-INCREMENT"
        reason = "beta-0.1 did not clear both material primary gates versus classical"
    elif not beta_zero_gate:
        classification = "NO-BETA-ZERO-INCREMENT"
        reason = "beta-0.1 did not clear both paired gates versus beta-zero"
    elif not guards_pass:
        classification = "LIMITED-REVERSAL-GUARD-FAIL"
        reason = "efficacy cleared but an unchanged physical or tail guard failed"
    else:
        classification = "LIMITED-REVERSAL-INCREMENT"
        reason = "beta-0.1 cleared classical, paired beta-zero, seed, tail, and physical gates"
    return {
        "classification": classification,
        "reason": reason,
        "efficacy_and_guard_gates": gates,
    }
