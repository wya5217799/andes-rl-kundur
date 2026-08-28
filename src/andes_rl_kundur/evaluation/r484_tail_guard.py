"""Pure R484 30-second tail summaries, guards, and sensitivity analysis.

R484 extends the *frozen* R483 final policies to a 150-step horizon.  This
module deliberately owns no simulator, checkpoint loading, or file I/O.  It
adds a fail-closed completeness layer around the established physical
estimators, reports all 832 learned policy-profile decisions, reuses the
exact R481 Phase-1A deterministic gate, and keeps the 30-second source
factorial sensitivity separate from the six-second R483 primary analysis.

All public results contain JSON-native values in deterministic roster order,
so a formal runner can write them with create-only + SHA-256-sidecar I/O.
Missing, duplicate, nonfinite, incomplete, or unexpected rows never become an
available-case scientific result.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import summarise_profile
from andes_rl_kundur.evaluation.r481_fresh_profiles import phase1a_gate
from andes_rl_kundur.evaluation.r482_analysis import (
    INTERACTIONS,
    MAIN_EFFECTS,
    boundary_test_rows,
)
from andes_rl_kundur.evaluation.source_factorial_design import (
    holm_decisions,
    seed_effects,
)

ROUND_ID = "R484"
EXPECTED_STEPS = 150
DT_SECONDS = 0.2
EXPECTED_PROFILE_COUNT = 4
EXPECTED_POLICY_COUNT = 208
EXPECTED_LEARNED_PROFILE_BLOCKS = EXPECTED_POLICY_COUNT * EXPECTED_PROFILE_COUNT
DETERMINISTIC_ARM = "local_neighbour_md_km2_kd2"
ZERO_ARM = "zero"
EXPECTED_CANARY_PROFILES = tuple(f"canary_eval_{letter}" for letter in "abcd")
EXPECTED_FRESH_PROFILES = tuple(f"fresh_eva_{letter}" for letter in "abcd")
EXPECTED_R483_SEEDS = tuple(range(501, 527))
R483_ARM_FACTORS: dict[str, tuple[str, str, int]] = {
    f"a{actor.lower()}_c{critic.lower()}_r{reward}": (actor, critic, reward)
    for actor in ("N", "P")
    for critic in ("N", "P")
    for reward in (0, 1)
}
EXPECTED_R483_POLICIES = frozenset(
    (arm, seed) for arm in R483_ARM_FACTORS for seed in EXPECTED_R483_SEEDS
)

DEFAULT_THRESHOLDS: dict[str, float] = {
    "minimum_joint_improvement": 0.05,
    "maximum_common_harm": 0.03,
    "maximum_action_stress_harm": 0.10,
    "maximum_action_saturation_fraction": 0.05,
    "nonconstant_action_variation_floor": 1.0e-6,
    "independent_action_dispersion_floor": 1.0e-6,
}

_SUMMARY_NUMERIC_KEYS = (
    "off_diagonal_response_energy",
    "disturbance_differential_energy",
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
    "minimum_record_total_variation",
    "maximum_action_row_dispersion",
    "minimum_record_action_row_dispersion",
    "action_saturation_fraction",
)


def _all_numeric_finite(value: object) -> bool:
    """Recursively reject NaN/Inf in a raw trajectory row."""

    if isinstance(value, bool) or value is None or isinstance(value, str):
        return True
    if isinstance(value, (int, float, np.integer, np.floating)):
        return math.isfinite(float(value))
    if isinstance(value, Mapping):
        return all(_all_numeric_finite(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return all(_all_numeric_finite(item) for item in value)
    return True


def _shared_optional(records: Sequence[Mapping[str, Any]], key: str) -> Any:
    values = [record.get(key) for record in records]
    first = values[0]
    if any(value != first for value in values[1:]):
        raise ValueError(f"profile records disagree on {key}")
    return first


def summarise_30s_profile(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    expected_steps: int = EXPECTED_STEPS,
    round_id: str = ROUND_ID,
) -> dict[str, Any]:
    """Summarise one complete six-scenario, 30-second profile block.

    The canonical R399 estimator supplies the metric definitions.  R484 adds
    exact trajectory-length, step-order, completion, TDS, failure, and finite
    row checks before invoking it.  The contract must itself bind 150 x 0.2 s;
    callers cannot silently turn this into another horizon.
    """

    if expected_steps != EXPECTED_STEPS:
        raise ValueError(f"R484 requires exactly {EXPECTED_STEPS} steps")
    if int(contract.get("steps", -1)) != expected_steps:
        raise ValueError("contract step count is not the registered R484 horizon")
    if not math.isclose(
        float(contract.get("dt_seconds", math.nan)),
        DT_SECONDS,
        rel_tol=0.0,
        abs_tol=0.0,
    ):
        raise ValueError("contract dt is not the registered R484 sample time")
    if len(records) != 6:
        raise ValueError("R484 profile block requires exactly six records")

    for record in records:
        steps = record.get("steps")
        if not isinstance(steps, list) or len(steps) != expected_steps:
            raise ValueError("R484 record must contain exactly 150 step rows")
        if record.get("completed") is not True:
            raise ValueError("R484 record is not complete")
        if record.get("tds_failed") is not False:
            raise ValueError("R484 record contains a TDS failure")
        if record.get("failure") not in (None, ""):
            raise ValueError("R484 record contains an explicit failure")
        if "completed_steps" in record and int(record["completed_steps"]) != expected_steps:
            raise ValueError("R484 completed_steps does not match the horizon")
        indices = [step.get("step_index") for step in steps]
        if indices != list(range(expected_steps)):
            raise ValueError("R484 step indices must be exactly 0..149")
        if any(step.get("tds_failed") is not False for step in steps):
            raise ValueError("R484 step row contains a TDS failure")
        if any(step.get("done") is not (index == expected_steps - 1) for index, step in enumerate(steps)):
            raise ValueError("R484 done flags must be false until the final step")
        times = np.asarray([step.get("time", math.nan) for step in steps], dtype=float)
        if not np.all(np.isfinite(times)) or not np.allclose(
            np.diff(times), DT_SECONDS, rtol=0.0, atol=1.0e-9
        ):
            raise ValueError("R484 trajectory time grid is incomplete or irregular")
        if not _all_numeric_finite(record):
            raise ValueError("R484 trajectory contains a nonfinite numeric value")

    training_seed = _shared_optional(records, "training_seed")
    checkpoint_sha256 = _shared_optional(records, "checkpoint_sha256")
    training_manifest_sha256 = _shared_optional(records, "training_manifest_sha256")
    stage = _shared_optional(records, "stage")
    summary = dict(summarise_profile(records, contract=contract))
    summary.update(
        {
            "round": str(round_id),
            "expected_steps": expected_steps,
            "horizon_seconds": expected_steps * DT_SECONDS,
            "completion_pass": True,
            "tds_pass": True,
            "training_seed": training_seed,
            "checkpoint_sha256": checkpoint_sha256,
            "training_manifest_sha256": training_manifest_sha256,
            "stage": stage,
        }
    )
    return summary


def _normalise_policy(value: object) -> tuple[str, int]:
    if isinstance(value, Mapping):
        arm = str(value.get("arm_id", ""))
        seed_raw = value.get("training_seed", value.get("seed"))
        if seed_raw is None:
            raise ValueError("learned policy is missing its seed")
        seed = int(seed_raw)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        if len(value) != 2:
            raise ValueError("learned policy tuple must contain arm and seed")
        arm = str(value[0])
        seed = int(value[1])
    else:
        raise ValueError("learned policy roster entry has an invalid shape")
    if not arm or seed < 1:
        raise ValueError("learned policy identity is invalid")
    return arm, seed


def _summary_integrity_errors(
    summary: Mapping[str, Any], *, require_checkpoint: bool
) -> list[str]:
    errors: list[str] = []
    try:
        numeric = np.asarray(
            [float(summary[key]) for key in _SUMMARY_NUMERIC_KEYS], dtype=float
        )
    except (KeyError, TypeError, ValueError):
        numeric = np.asarray([math.nan])
        errors.append("missing_or_invalid_metric")
    if not np.all(np.isfinite(numeric)) or np.any(numeric < 0.0):
        errors.append("nonfinite_or_negative_metric")
    checks = {
        "valid": summary.get("valid") is True,
        "six_records": summary.get("record_count") == 6,
        "expected_steps": summary.get("expected_steps") == EXPECTED_STEPS,
        "horizon_seconds": summary.get("horizon_seconds") == EXPECTED_STEPS * DT_SECONDS,
        "completion": summary.get("completion_pass") is True,
        "tds": summary.get("tds_pass") is True,
        "evaluation_split": summary.get("split") == "evaluation",
        "mapping": summary.get("actuator_mapping_pass") is True,
        "action_box": summary.get("action_bound_violation") is False,
        "action_slew": summary.get("action_slew_violation") is False,
    }
    errors.extend(name for name, passed in checks.items() if not passed)
    try:
        saturation = float(summary["action_saturation_fraction"])
    except (KeyError, TypeError, ValueError):
        saturation = math.nan
    if not math.isfinite(saturation) or not 0.0 <= saturation <= 1.0:
        errors.append("invalid_saturation_fraction")
    if require_checkpoint:
        for key in ("checkpoint_sha256", "training_manifest_sha256"):
            value = str(summary.get(key, ""))
            if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
                errors.append(f"invalid_{key}")
        if summary.get("stage") != "final":
            errors.append("not_final_checkpoint")
    return sorted(set(errors))


def _invalid_result(kind: str, errors: Sequence[str]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "classification": "INTEGRITY-INVALID",
        "analysis_kind": kind,
        "integrity_errors": sorted(set(str(error) for error in errors)),
        "scientific_outcome": "NOT_TESTED",
    }


def classify_learned_guard(
    summaries: Sequence[Mapping[str, Any]],
    *,
    policies: Sequence[object],
    profiles: Sequence[str],
    deterministic_arm: str = DETERMINISTIC_ARM,
    thresholds: Mapping[str, float] | None = None,
    deterministic_reference_gate: Mapping[str, Any] | None = None,
    round_id: str = ROUND_ID,
    policy_label: str = "R483",
    require_complete_policy_roster: bool = True,
) -> dict[str, Any]:
    """Classify complete profile blocks for the supplied policy roster."""

    try:
        policy_roster = tuple(sorted(_normalise_policy(value) for value in policies))
    except (TypeError, ValueError) as exc:
        return _invalid_result("learned_complete_guard", [str(exc)])
    profile_roster = tuple(sorted(str(value) for value in profiles))
    errors: list[str] = []
    if require_complete_policy_roster and (
        set(policy_roster) != EXPECTED_R483_POLICIES
        or len(policy_roster) != EXPECTED_POLICY_COUNT
    ):
        errors.append("policy_roster_must_match_the_exact_208_R483_final_policies")
    elif not policy_roster or len(set(policy_roster)) != len(policy_roster):
        errors.append("policy_roster_must_be_nonempty_and_unique")
    if set(profile_roster) != set(EXPECTED_CANARY_PROFILES) or len(profile_roster) != EXPECTED_PROFILE_COUNT:
        errors.append("profile_roster_must_match_the_four_registered_canary_profiles")

    expected = {
        (profile_id, arm, seed)
        for arm, seed in policy_roster
        for profile_id in profile_roster
    } | {(profile_id, deterministic_arm, None) for profile_id in profile_roster}
    by_key: dict[tuple[str, str, int | None], Mapping[str, Any]] = {}
    duplicates: list[tuple[str, str, int | None]] = []
    for index, summary in enumerate(summaries):
        seed_raw = summary.get("training_seed")
        try:
            seed = None if seed_raw is None else int(seed_raw)
        except (TypeError, ValueError):
            errors.append(f"summary{index}:invalid_training_seed")
            continue
        key = (str(summary.get("profile_id", "")), str(summary.get("arm_id", "")), seed)
        if key in by_key:
            duplicates.append(key)
        by_key[key] = summary
    if duplicates:
        errors.append(f"duplicate_summary:{duplicates[0]}")
    missing = sorted(expected - set(by_key))
    unexpected = sorted(set(by_key) - expected)
    if missing:
        errors.append(f"missing_summary:{missing[0]}")
    if unexpected:
        errors.append(f"unexpected_summary:{unexpected[0]}")
    for key in sorted(expected & set(by_key)):
        row_errors = _summary_integrity_errors(
            by_key[key], require_checkpoint=key[2] is not None
        )
        errors.extend(f"{key}:{error}" for error in row_errors)
    for arm, seed in policy_roster:
        policy_rows = [
            by_key[(profile_id, arm, seed)]
            for profile_id in profile_roster
            if (profile_id, arm, seed) in by_key
        ]
        if len(policy_rows) == EXPECTED_PROFILE_COUNT:
            for hash_key in ("checkpoint_sha256", "training_manifest_sha256"):
                if len({str(row.get(hash_key, "")) for row in policy_rows}) != 1:
                    errors.append(f"{arm}|{seed}:inconsistent_{hash_key}")
    for profile_id in profile_roster:
        reference = by_key.get((profile_id, deterministic_arm, None))
        if reference is not None:
            for endpoint in (
                "off_diagonal_response_energy",
                "disturbance_differential_energy",
            ):
                if float(reference[endpoint]) <= 0.0:
                    errors.append(
                        f"{profile_id}:nonpositive_deterministic_reference:{endpoint}"
                    )
    if errors:
        return _invalid_result("learned_complete_guard", errors)

    limits = {**DEFAULT_THRESHOLDS, **dict(thresholds or {})}
    minimum_joint_improvement = float(limits["minimum_joint_improvement"])
    if not 0.0 < minimum_joint_improvement < 1.0:
        return _invalid_result(
            "learned_complete_guard", ["minimum_joint_improvement_must_be_in_(0,1)"]
        )
    common_harm = float(limits["maximum_common_harm"])
    stress_harm = float(limits["maximum_action_stress_harm"])
    saturation_limit = float(limits["maximum_action_saturation_fraction"])
    variation_floor = float(limits["nonconstant_action_variation_floor"])
    dispersion_floor = float(limits["independent_action_dispersion_floor"])

    profile_blocks: list[dict[str, Any]] = []
    policy_decisions: list[dict[str, Any]] = []
    for arm, seed in policy_roster:
        failed_profiles: list[str] = []
        passed_count = 0
        for profile_id in profile_roster:
            candidate = by_key[(profile_id, arm, seed)]
            reference = by_key[(profile_id, deterministic_arm, None)]
            guard = {
                "valid": candidate.get("valid") is True,
                "actuator_mapping_pass": candidate.get("actuator_mapping_pass") is True,
                "action_bound_violation": candidate.get("action_bound_violation") is False,
                "action_slew_violation": candidate.get("action_slew_violation") is False,
                "common_frequency_no_harm": float(candidate["common_frequency_iae_hz_s"])
                <= (1.0 + common_harm) * float(reference["common_frequency_iae_hz_s"]) + 1.0e-15,
                "worst_peak_no_harm": float(candidate["worst_unit_peak_hz"])
                <= (1.0 + common_harm) * float(reference["worst_unit_peak_hz"]) + 1.0e-15,
                "rocof_no_harm": float(candidate["worst_rocof_hz_s"])
                <= (1.0 + common_harm) * float(reference["worst_rocof_hz_s"]) + 1.0e-15,
                "action_rms_no_harm": float(candidate["action_rms"])
                <= (1.0 + stress_harm) * float(reference["action_rms"]) + 1.0e-15,
                "action_variation_no_harm": float(candidate["action_total_variation"])
                <= (1.0 + stress_harm) * float(reference["action_total_variation"]) + 1.0e-15,
                "saturation_budget": float(candidate["action_saturation_fraction"])
                <= saturation_limit,
                "nonconstant_action": float(candidate["minimum_record_total_variation"])
                > variation_floor,
                "independent_per_vsg_action": float(candidate["minimum_record_action_row_dispersion"])
                > dispersion_floor,
            }
            passed = bool(all(guard.values()))
            if passed:
                passed_count += 1
            else:
                failed_profiles.append(profile_id)
            profile_blocks.append(
                {
                    "arm_id": arm,
                    "training_seed": seed,
                    "profile_id": profile_id,
                    "passed": passed,
                    "guard": guard,
                    "failed_guards": sorted(name for name, value in guard.items() if not value),
                    "off_diagonal_ratio_to_deterministic": float(
                        candidate["off_diagonal_response_energy"]
                    )
                    / float(reference["off_diagonal_response_energy"]),
                    "differential_ratio_to_deterministic": float(
                        candidate["disturbance_differential_energy"]
                    )
                    / float(reference["disturbance_differential_energy"]),
                    "endpoint_ratios_are_report_lines_not_profile_gates": True,
                }
            )
        candidate_off_diagonal = sum(
            float(by_key[(profile_id, arm, seed)]["off_diagonal_response_energy"])
            for profile_id in profile_roster
        )
        reference_off_diagonal = sum(
            float(
                by_key[(profile_id, deterministic_arm, None)][
                    "off_diagonal_response_energy"
                ]
            )
            for profile_id in profile_roster
        )
        candidate_differential = sum(
            float(
                by_key[(profile_id, arm, seed)][
                    "disturbance_differential_energy"
                ]
            )
            for profile_id in profile_roster
        )
        reference_differential = sum(
            float(
                by_key[(profile_id, deterministic_arm, None)][
                    "disturbance_differential_energy"
                ]
            )
            for profile_id in profile_roster
        )
        endpoint_ratios = {
            "off_diagonal_response_energy": candidate_off_diagonal
            / reference_off_diagonal,
            "disturbance_differential_energy": candidate_differential
            / reference_differential,
        }
        endpoint_target = {
            name: value <= (1.0 - minimum_joint_improvement) + 1.0e-15
            for name, value in endpoint_ratios.items()
        }
        profile_guards_passed = passed_count == EXPECTED_PROFILE_COUNT
        complete_guard_passed = bool(
            profile_guards_passed and all(endpoint_target.values())
        )
        policy_decisions.append(
            {
                "arm_id": arm,
                "training_seed": seed,
                "passed_complete_guard": complete_guard_passed,
                "passed_4_of_4": complete_guard_passed,
                "profile_guards_passed_4_of_4": profile_guards_passed,
                "passed_count": passed_count,
                "failed_profiles": failed_profiles,
                "aggregate_endpoint_ratios_to_deterministic": endpoint_ratios,
                "aggregate_joint_endpoint_target": endpoint_target,
                "endpoint_aggregation": "equal_weight_sum_over_four_profiles",
            }
        )

    passing = [
        {"arm_id": row["arm_id"], "training_seed": row["training_seed"]}
        for row in policy_decisions
        if row["passed_complete_guard"]
    ]
    raw_guard_classification = (
        f"{policy_label}-FROZEN-POLICIES-ALL-FAIL-COMPLETE-GUARD"
        if not passing
        else f"{policy_label}-FROZEN-POLICIES-SOME-PASS-COMPLETE-GUARD"
    )
    gate_payload: Mapping[str, Any] = (
        deterministic_reference_gate.get("gate", deterministic_reference_gate)
        if isinstance(deterministic_reference_gate, Mapping)
        else {}
    )
    gate_container_valid = bool(
        not isinstance(deterministic_reference_gate, Mapping)
        or "gate" not in deterministic_reference_gate
        or deterministic_reference_gate.get("classification")
        == "DIRECT-MD-30S-CANARY-DESCRIPTIVE-PASS"
    )
    gate_profiles = gate_payload.get("per_profile", {})
    reference_gate_4_of_4 = bool(
        gate_container_valid
        and gate_payload.get("passed_4_of_4") is True
        and gate_payload.get("passed_count") == EXPECTED_PROFILE_COUNT
        and gate_payload.get("selected_arm") == deterministic_arm
        and isinstance(gate_profiles, Mapping)
        and set(str(key) for key in gate_profiles) == set(profile_roster)
        and all(
            isinstance(gate_profiles[profile_id], Mapping)
            and gate_profiles[profile_id].get("passed") is True
            for profile_id in profile_roster
        )
    )
    classification = (
        raw_guard_classification
        if reference_gate_4_of_4
        else "LEARNED-COMPLETE-GUARD-REFERENCE-INVALID"
    )
    return {
        "schema_version": 1,
        "round": str(round_id),
        "analysis_kind": "learned_complete_guard",
        "classification": classification,
        "scientific_outcome": (
            raw_guard_classification if reference_gate_4_of_4 else "NOT_TESTED"
        ),
        "raw_guard_classification": raw_guard_classification,
        "checks": {
            "complete_roster": True,
            "all_summaries_integrity_valid": True,
            "profile_block_count": len(profile_blocks),
            "policy_decision_count": len(policy_decisions),
            "probability_claim": False,
            "minimum_joint_improvement": minimum_joint_improvement,
            "deterministic_reference_gate_4_of_4": reference_gate_4_of_4,
        },
        "per_profile_blocks": profile_blocks,
        "policy_decisions": policy_decisions,
        "passing_count": len(passing),
        "passing_roster": passing,
        "claim_scope": f"208 frozen {policy_label} final policies on four registered canary profiles only",
    }


def classify_deterministic_tail(
    summaries: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any],
    selected_arm: str = DETERMINISTIC_ARM,
    expected_profiles: Sequence[str],
    bank_name: str,
    round_id: str = ROUND_ID,
) -> dict[str, Any]:
    """Apply the exact R481 Phase-1A gate to one four-profile 30-second bank."""

    normalized_bank = bank_name.strip().lower()
    if normalized_bank not in {"fresh", "canary"}:
        raise ValueError("bank_name must be 'fresh' or 'canary'")
    profiles = tuple(sorted(str(value) for value in expected_profiles))
    errors: list[str] = []
    registered_profiles = (
        EXPECTED_FRESH_PROFILES
        if normalized_bank == "fresh"
        else EXPECTED_CANARY_PROFILES
    )
    if set(profiles) != set(registered_profiles) or len(profiles) != EXPECTED_PROFILE_COUNT:
        errors.append(f"{normalized_bank}_profile_roster_mismatch")
    contract_profiles = {
        str(profile["profile_id"])
        for profile in contract.get("profiles", [])
        if profile.get("split") == "evaluation"
    }
    if contract_profiles != set(profiles):
        errors.append("contract_evaluation_profile_roster_mismatch")
    expected = {
        (profile_id, arm_id)
        for profile_id in profiles
        for arm_id in (ZERO_ARM, selected_arm)
    }
    by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicates: list[tuple[str, str]] = []
    for summary in summaries:
        key = (str(summary.get("profile_id", "")), str(summary.get("arm_id", "")))
        if key in by_key:
            duplicates.append(key)
        by_key[key] = summary
    if duplicates:
        errors.append(f"duplicate_summary:{duplicates[0]}")
    missing = sorted(expected - set(by_key))
    unexpected = sorted(set(by_key) - expected)
    if missing:
        errors.append(f"missing_summary:{missing[0]}")
    if unexpected:
        errors.append(f"unexpected_summary:{unexpected[0]}")
    for key in sorted(expected & set(by_key)):
        errors.extend(
            f"{key}:{error}"
            for error in _summary_integrity_errors(by_key[key], require_checkpoint=False)
        )
    if errors:
        return _invalid_result(f"deterministic_{bank_name}_tail", errors)

    gate = phase1a_gate(
        [by_key[key] for key in sorted(by_key)],
        contract=contract,
        selected_arm=selected_arm,
    )
    if normalized_bank == "fresh":
        classification = (
            "DIRECT-MD-30S-FRESH-PASS"
            if gate["passed_4_of_4"]
            else "DIRECT-MD-30S-FRESH-FAIL"
        )
    elif normalized_bank == "canary":
        classification = (
            "DIRECT-MD-30S-CANARY-DESCRIPTIVE-PASS"
            if gate["passed_4_of_4"]
            else "DIRECT-MD-30S-CANARY-DESCRIPTIVE-FAIL"
        )
    return {
        "schema_version": 1,
        "round": str(round_id),
        "analysis_kind": f"deterministic_{normalized_bank}_tail",
        "classification": classification,
        "scientific_outcome": classification,
        "checks": {"complete_roster": True, "all_summaries_integrity_valid": True},
        "gate": gate,
        "descriptive_only": normalized_bank == "canary",
    }


def analyse_tail_factorial(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_seeds: Sequence[int],
    expected_profiles: Sequence[str],
) -> dict[str, Any]:
    """Compute the registered four-effect 30-second sensitivity, never pooled."""

    normalized: list[dict[str, Any]] = []
    errors: list[str] = []
    if tuple(sorted(int(value) for value in expected_seeds)) != EXPECTED_R483_SEEDS:
        errors.append("factorial_seed_roster_must_match_501_through_526")
    if set(str(value) for value in expected_profiles) != set(EXPECTED_CANARY_PROFILES):
        errors.append("factorial_profile_roster_must_match_registered_canary_profiles")
    for index, row in enumerate(rows):
        row_errors = _summary_integrity_errors(row, require_checkpoint=True)
        errors.extend(f"row{index}:{error}" for error in row_errors)
        arm_id = str(row.get("arm_id", ""))
        expected_factors = R483_ARM_FACTORS.get(arm_id)
        try:
            reward_access = int(row.get("reward_access", -1))
        except (TypeError, ValueError):
            reward_access = -1
        actual_factors = (
            str(row.get("actor_source", "")),
            str(row.get("critic_source", "")),
            reward_access,
        )
        if expected_factors != actual_factors:
            errors.append(f"row{index}:arm_factor_mapping_mismatch")
        normalized.append(
            {
                "stage": row.get("stage"),
                "seed": row.get("seed", row.get("training_seed")),
                "actor_source": row.get("actor_source"),
                "critic_source": row.get("critic_source"),
                "reward_access": row.get("reward_access"),
                "profile": row.get("profile", row.get("profile_id")),
                "disturbance_differential_energy": row.get("disturbance_differential_energy"),
            }
        )
    if errors:
        return _invalid_result("tail_factorial_sensitivity", errors)
    try:
        effects = seed_effects(
            normalized,
            expected_seeds=expected_seeds,
            expected_profiles=expected_profiles,
        )
        tests = boundary_test_rows(effects, math.log(1.10))
        decisions = holm_decisions(
            {name: float(row["p_one_sided"]) for name, row in tests.items()}
        )
    except (KeyError, TypeError, ValueError) as exc:
        return _invalid_result("tail_factorial_sensitivity", [str(exc)])
    for name in sorted(tests):
        tests[name]["holm"] = decisions[name]
    main = any(bool(decisions[name]["reject"]) for name in MAIN_EFFECTS)
    interaction = any(bool(decisions[name]["reject"]) for name in INTERACTIONS)
    if main and interaction:
        classification = "TAIL-MATERIAL-MAIN-EFFECT+TAIL-MATERIAL-INTERACTION"
    elif main:
        classification = "TAIL-MATERIAL-MAIN-EFFECT"
    elif interaction:
        classification = "TAIL-MATERIAL-INTERACTION"
    else:
        classification = "TAIL-MATERIAL-EFFECT-NOT-ESTABLISHED"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "analysis_kind": "tail_factorial_sensitivity",
        "classification": classification,
        "scientific_outcome": classification,
        "horizon_seconds": EXPECTED_STEPS * DT_SECONDS,
        "materiality_ratio": 1.10,
        "seed_effects": {
            name: {str(seed): float(value) for seed, value in sorted(by_seed.items())}
            for name, by_seed in sorted(effects.items())
        },
        "test_rows": {name: tests[name] for name in sorted(tests)},
        "pooled_with_r483_six_second_primary": False,
        "substitutes_for_r483_primary": False,
    }


def classify_r484(
    *,
    design_valid: bool,
    missing_shards: Sequence[str],
    engineering_errors: Sequence[str],
    integrity_errors: Sequence[str],
    learned_guard: Mapping[str, Any] | None,
    fresh_tail: Mapping[str, Any] | None,
    canary_tail: Mapping[str, Any] | None,
    tail_factorial: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Apply R484 precedence without inventing a combined scientific verdict."""

    child_results = {
        "learned_guard": learned_guard,
        "fresh_tail": fresh_tail,
        "canary_tail": canary_tail,
        "tail_factorial": tail_factorial,
    }
    child_invalid = sorted(
        name
        for name, value in child_results.items()
        if not isinstance(value, Mapping)
        or value.get("classification") == "INTEGRITY-INVALID"
    )
    if not design_valid:
        classification = "DESIGN-INVALID"
    elif missing_shards or engineering_errors:
        classification = "ENGINEERING-INVALID"
    elif integrity_errors or child_invalid:
        classification = "INTEGRITY-INVALID"
    else:
        classification = "R484-VALID"
    scientific_valid = classification == "R484-VALID"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "classification": classification,
        "checks": {
            "design_valid": bool(design_valid),
            "execution_complete": not missing_shards,
            "engineering_pass": not engineering_errors,
            "integrity_pass": not integrity_errors and not child_invalid,
        },
        "missing_shards": sorted(set(str(value) for value in missing_shards)),
        "engineering_errors": sorted(set(str(value) for value in engineering_errors)),
        "integrity_errors": sorted(
            set([*(str(value) for value in integrity_errors), *child_invalid])
        ),
        "outcomes": {
            name: (
                value.get("scientific_outcome", "NOT_TESTED")
                if scientific_valid and isinstance(value, Mapping)
                else "NOT_TESTED"
            )
            for name, value in child_results.items()
        },
        "scientific_results_valid": scientific_valid,
    }


__all__ = [
    "DEFAULT_THRESHOLDS",
    "DETERMINISTIC_ARM",
    "DT_SECONDS",
    "EXPECTED_CANARY_PROFILES",
    "EXPECTED_FRESH_PROFILES",
    "EXPECTED_LEARNED_PROFILE_BLOCKS",
    "EXPECTED_POLICY_COUNT",
    "EXPECTED_PROFILE_COUNT",
    "EXPECTED_R483_POLICIES",
    "EXPECTED_R483_SEEDS",
    "EXPECTED_STEPS",
    "R483_ARM_FACTORS",
    "ROUND_ID",
    "ZERO_ARM",
    "analyse_tail_factorial",
    "classify_deterministic_tail",
    "classify_learned_guard",
    "classify_r484",
    "summarise_30s_profile",
]
