"""R403 disclosed-profile development gate for the repaired CD-MATD3.

This module contains only the frozen small-fast contract and deterministic
classification logic.  The WSL adapter owns execution; this seam stays pure
so the kill decision can be regression-tested without ANDES.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any

from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract

ROUND_ID = "R403"
SCRATCH_SEED = 4030
TOTAL_INTERACTION_STEPS = 1200
REPAIRED_ARMS = ("cd_matd3_no_message", "cd_matd3_message")
R402_BASELINE = "r402_cd_matd3_message_seed403"
DETERMINISTIC_BASELINE = "deterministic_reference"


def build_successor_contract() -> dict[str, Any]:
    """Return the frozen R403 repair and disclosed-development contract."""

    base = build_contract()
    development = [
        copy.deepcopy(profile)
        for profile in base["profiles"]
        if profile["split"] == "development"
    ]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": "yang-md-decoupling-marl",
        "source_contract_sha256": _canonical_sha256(base),
        "profiles": development,
        "excluded_profile_ids": [
            str(profile["profile_id"])
            for profile in base["profiles"]
            if profile["split"] != "development"
        ],
        "scenario_order": list(
            base["training_contract"]["development_scenario_order"]
        ),
        "steps_per_episode": int(base["steps"]),
        "total_interaction_steps": TOTAL_INTERACTION_STEPS,
        "scratch_seed": SCRATCH_SEED,
        "repaired_arms": list(REPAIRED_ARMS),
        "fixed_common_weight": 1.0,
        "action_effort_weight": 1.0,
        "action_slew_limit": float(base["action_slew_limit"]),
        "physical_nominal_frequency_hz": float(
            base["physical_nominal_frequency_hz"]
        ),
        "dt_seconds": float(base["dt_seconds"]),
        "differential_transform": copy.deepcopy(base["differential_transform"]),
        "learner_contract": copy.deepcopy(base["learner_contract"]),
        "reward_contract": copy.deepcopy(base["reward_contract"]),
        "r402_baseline": {
            "arm_id": "cd_matd3_message",
            "seed": 403,
        },
        "acceptance": {
            "slew_bound_hit_fraction_strict_upper": 0.05,
            "mean_abs_action_strictly_below_r402": True,
            "common_cost_ratio_to_deterministic_max": 1.5,
            "differential_cost_ratio_to_r402_max": 1.0,
            "tds_failed_episodes_max": 0,
            "finite_complete_diagnostics": True,
        },
    }


def contract_sha256(contract: Mapping[str, Any] | None = None) -> str:
    """Return the canonical digest of the successor contract."""

    return _canonical_sha256(
        build_successor_contract() if contract is None else contract
    )


def classify_development_gate(
    metrics: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify both repaired arms against the two matched baselines."""

    required = {*REPAIRED_ARMS, R402_BASELINE, DETERMINISTIC_BASELINE}
    missing = sorted(required - set(metrics))
    if missing:
        return {
            "classification": "SCRATCH-INVALID",
            "missing_metric_blocks": missing,
            "arm_decisions": {},
        }

    r402 = metrics[R402_BASELINE]
    deterministic = metrics[DETERMINISTIC_BASELINE]
    arm_decisions: dict[str, Any] = {}
    for arm_id in REPAIRED_ARMS:
        candidate = metrics[arm_id]
        finite = _all_finite(candidate)
        complete = bool(candidate.get("diagnostics_complete", False))
        no_tds_failure = int(candidate.get("tds_failed_episodes", -1)) == 0
        slew_ok = (
            float(candidate["slew_bound_hit_fraction"]) < 0.05
            if finite
            else False
        )
        action_ok = (
            float(candidate["mean_abs_action"])
            < float(r402["mean_abs_action"])
            if finite and _all_finite(r402)
            else False
        )
        common_ratio = _safe_ratio(
            candidate.get("mean_per_record_common"),
            deterministic.get("mean_per_record_common"),
        )
        differential_ratio = _safe_ratio(
            candidate.get("mean_per_record_differential"),
            r402.get("mean_per_record_differential"),
        )
        common_ok = common_ratio is not None and common_ratio <= 1.5
        differential_ok = (
            differential_ratio is not None and differential_ratio <= 1.0
        )
        guards = {
            "finite": finite,
            "diagnostics_complete": complete,
            "no_tds_failure": no_tds_failure,
            "slew_ok": slew_ok,
            "action_ok": action_ok,
            "common_ok": common_ok,
            "differential_ok": differential_ok,
        }
        arm_decisions[arm_id] = {
            "passed": all(guards.values()),
            "guards": guards,
            "common_ratio_to_deterministic": common_ratio,
            "differential_ratio_to_r402": differential_ratio,
        }
    classification = (
        "SCRATCH-PASS"
        if all(value["passed"] for value in arm_decisions.values())
        else "SCRATCH-FAIL"
    )
    return {
        "classification": classification,
        "missing_metric_blocks": [],
        "arm_decisions": arm_decisions,
    }


def _canonical_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _all_finite(block: Mapping[str, Any]) -> bool:
    keys = (
        "mean_abs_action",
        "slew_bound_hit_fraction",
        "mean_per_record_common",
        "mean_per_record_differential",
    )
    try:
        values = [float(block[key]) for key in keys]
    except (KeyError, TypeError, ValueError):
        return False
    return all(value == value and abs(value) != float("inf") for value in values)


def _safe_ratio(numerator: Any, denominator: Any) -> float | None:
    try:
        top = float(numerator)
        bottom = float(denominator)
    except (TypeError, ValueError):
        return None
    if not all(value == value and abs(value) != float("inf") for value in (top, bottom)):
        return None
    if bottom <= 0.0:
        return 0.0 if top <= 0.0 else None
    return top / bottom


__all__ = [
    "DETERMINISTIC_BASELINE",
    "R402_BASELINE",
    "REPAIRED_ARMS",
    "ROUND_ID",
    "SCRATCH_SEED",
    "TOTAL_INTERACTION_STEPS",
    "build_successor_contract",
    "classify_development_gate",
    "contract_sha256",
]
