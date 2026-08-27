from __future__ import annotations

import json
import math

import numpy as np

from andes_rl_kundur.evaluation import r482_analysis
from andes_rl_kundur.evaluation.cd_matd3_canary import build_contract as build_canary
from andes_rl_kundur.evaluation.r481_fresh_profiles import build_contract as build_fresh
from andes_rl_kundur.evaluation.r484_tail_guard import (
    DETERMINISTIC_ARM,
    EXPECTED_STEPS,
    ZERO_ARM,
    analyse_tail_factorial,
    classify_deterministic_tail,
    classify_learned_guard,
    classify_r484,
    summarise_30s_profile,
)

PROFILES = tuple(f"canary_eval_{letter}" for letter in "abcd")
POLICIES = tuple(
    (arm, seed)
    for arm in (
        "an_cn_r0",
        "an_cn_r1",
        "an_cp_r0",
        "an_cp_r1",
        "ap_cn_r0",
        "ap_cn_r1",
        "ap_cp_r0",
        "ap_cp_r1",
    )
    for seed in range(501, 527)
)


def _trajectory_record(
    scenario: dict[str, object],
    profile: dict[str, object],
    *,
    arm_id: str = "an_cn_r0",
    seed: int | None = 501,
) -> dict[str, object]:
    baseline_m = np.asarray(profile["baseline_m0"], dtype=float)
    baseline_d = np.asarray(profile["baseline_d0"], dtype=float)
    kind_scale = {"common": 1.0, "differential": 0.7, "localized": 0.4}[
        str(scenario["pair_kind"])
    ]
    sign = 1.0 if scenario["sign"] == "positive" else -1.0
    steps: list[dict[str, object]] = []
    for index in range(EXPECTED_STEPS):
        envelope = math.exp(-index / 80.0)
        deviation = sign * kind_scale * 0.01 * envelope
        frequency = np.asarray([deviation, deviation * 0.8, -deviation * 0.4, -deviation * 0.2])
        action = np.zeros((4, 2), dtype=float)
        delta_m = np.zeros(4, dtype=float)
        delta_d = np.zeros(4, dtype=float)
        steps.append(
            {
                "step_index": index,
                "time": 0.7 + 0.2 * index,
                "freq_hz_physical": (60.0 + frequency).tolist(),
                "action_norm": action.tolist(),
                "raw_action_norm": action.tolist(),
                "delta_M": delta_m.tolist(),
                "delta_D": delta_d.tolist(),
                "M_es": baseline_m.tolist(),
                "D_es": baseline_d.tolist(),
                "tds_failed": False,
                "done": index == EXPECTED_STEPS - 1,
            }
        )
    record: dict[str, object] = {
        "profile_id": scenario["profile_id"],
        "scenario_id": scenario["scenario_id"],
        "pair_kind": scenario["pair_kind"],
        "sign": scenario["sign"],
        "magnitude": scenario["magnitude"],
        "arm_id": arm_id,
        "identity": {
            "baseline_m0": baseline_m.tolist(),
            "baseline_d0": baseline_d.tolist(),
        },
        "initial_freq_hz_physical": [60.0] * 4,
        "steps": steps,
        "completed": True,
        "completed_steps": EXPECTED_STEPS,
        "tds_failed": False,
        "failure": None,
        "training_seed": seed,
        "checkpoint_sha256": "a" * 64 if seed is not None else None,
        "training_manifest_sha256": "b" * 64 if seed is not None else None,
        "stage": "final" if seed is not None else None,
    }
    return record


def test_summarise_30s_profile_requires_complete_time_ordered_trajectory() -> None:
    contract = build_canary()
    contract["steps"] = EXPECTED_STEPS
    profile = next(row for row in contract["profiles"] if row["profile_id"] == PROFILES[0])
    records = [
        _trajectory_record(scenario, profile)
        for scenario in profile["scenarios"]
    ]

    summary = summarise_30s_profile(records, contract=contract)

    assert summary["valid"] is True
    assert summary["completion_pass"] is True
    assert summary["tds_pass"] is True
    assert summary["expected_steps"] == 150
    assert summary["horizon_seconds"] == 30.0
    assert summary["training_seed"] == 501
    assert summary["checkpoint_sha256"] == "a" * 64

    records[0]["steps"][-1]["done"] = False
    with np.testing.assert_raises_regex(ValueError, "done flags"):
        summarise_30s_profile(records, contract=contract)


def _summary(
    *,
    profile_id: str,
    arm_id: str,
    seed: int | None,
    off_diagonal: float = 10.0,
    differential: float = 10.0,
    common: float = 1.0,
    peak: float = 1.0,
    rocof: float = 1.0,
    action_rms: float = 0.5,
    action_variation: float = 1.0,
    minimum_variation: float = 0.1,
    dispersion: float = 0.1,
) -> dict[str, object]:
    learned = seed is not None
    return {
        "round": "R484",
        "profile_id": profile_id,
        "split": "evaluation",
        "arm_id": arm_id,
        "training_seed": seed,
        "stage": "final" if learned else None,
        "checkpoint_sha256": "a" * 64 if learned else None,
        "training_manifest_sha256": "b" * 64 if learned else None,
        "valid": True,
        "record_count": 6,
        "expected_steps": 150,
        "horizon_seconds": 30.0,
        "completion_pass": True,
        "tds_pass": True,
        "off_diagonal_response_energy": off_diagonal,
        "disturbance_differential_energy": differential,
        "common_frequency_iae_hz_s": common,
        "worst_unit_peak_hz": peak,
        "worst_rocof_hz_s": rocof,
        "action_rms": action_rms,
        "action_total_variation": action_variation,
        "minimum_record_total_variation": minimum_variation,
        "maximum_action_row_dispersion": dispersion,
        "minimum_record_action_row_dispersion": dispersion,
        "action_saturation_fraction": 0.0,
        "action_bound_violation": False,
        "action_slew_violation": False,
        "actuator_mapping_pass": True,
    }


def _complete_learned_bank() -> list[dict[str, object]]:
    rows = [
        _summary(
            profile_id=profile_id,
            arm_id=DETERMINISTIC_ARM,
            seed=None,
        )
        for profile_id in PROFILES
    ]
    rows.extend(
        _summary(
            profile_id=profile_id,
            arm_id=arm,
            seed=seed,
            off_diagonal=9.5,
            differential=9.5,
        )
        for arm, seed in POLICIES
        for profile_id in PROFILES
    )
    return rows


def _passing_canary_reference_gate() -> dict[str, object]:
    return {
        "passed_4_of_4": True,
        "passed_count": 4,
        "selected_arm": DETERMINISTIC_ARM,
        "per_profile": {
            profile_id: {"passed": True} for profile_id in PROFILES
        },
    }


def test_learned_guard_reports_all_832_blocks_and_208_policy_decisions() -> None:
    summaries = _complete_learned_bank()
    first = next(
        row
        for row in summaries
        if row["arm_id"] == POLICIES[0][0]
        and row["training_seed"] == POLICIES[0][1]
        and row["profile_id"] == PROFILES[0]
    )
    first["common_frequency_iae_hz_s"] = 1.04

    result = classify_learned_guard(
        summaries,
        policies=POLICIES,
        profiles=PROFILES,
        deterministic_reference_gate=_passing_canary_reference_gate(),
    )

    assert result["classification"] == "R483-FROZEN-POLICIES-SOME-PASS-COMPLETE-GUARD"
    assert len(result["per_profile_blocks"]) == 832
    assert len(result["policy_decisions"]) == 208
    assert result["passing_count"] == 207
    assert result["policy_decisions"][0]["passed_count"] == 3
    assert result["checks"]["probability_claim"] is False
    json.dumps(result, sort_keys=True, allow_nan=False)


def test_learned_guard_fails_closed_on_missing_or_duplicate_summary() -> None:
    summaries = _complete_learned_bank()
    result = classify_learned_guard(
        summaries[:-1],
        policies=POLICIES,
        profiles=PROFILES,
        deterministic_reference_gate=_passing_canary_reference_gate(),
    )
    assert result["classification"] == "INTEGRITY-INVALID"
    assert result["scientific_outcome"] == "NOT_TESTED"
    assert any("missing_summary" in error for error in result["integrity_errors"])


def test_joint_endpoint_target_is_equal_weight_aggregate_not_per_profile() -> None:
    summaries = _complete_learned_bank()
    arm, seed = POLICIES[0]
    policy_rows = {
        str(row["profile_id"]): row
        for row in summaries
        if row["arm_id"] == arm and row["training_seed"] == seed
    }
    policy_rows[PROFILES[0]]["off_diagonal_response_energy"] = 10.0
    policy_rows[PROFILES[1]]["off_diagonal_response_energy"] = 9.0

    passed = classify_learned_guard(
        summaries,
        policies=POLICIES,
        profiles=PROFILES,
        deterministic_reference_gate=_passing_canary_reference_gate(),
    )

    decision = passed["policy_decisions"][0]
    first_profile = passed["per_profile_blocks"][0]
    assert first_profile["off_diagonal_ratio_to_deterministic"] == 1.0
    assert first_profile["passed"] is True
    assert decision["profile_guards_passed_4_of_4"] is True
    assert decision["aggregate_endpoint_ratios_to_deterministic"][
        "off_diagonal_response_energy"
    ] == 0.95
    assert decision["passed_complete_guard"] is True

    policy_rows[PROFILES[1]]["off_diagonal_response_energy"] = 9.01
    failed = classify_learned_guard(
        summaries,
        policies=POLICIES,
        profiles=PROFILES,
        deterministic_reference_gate=_passing_canary_reference_gate(),
    )
    decision = failed["policy_decisions"][0]
    assert decision["profile_guards_passed_4_of_4"] is True
    assert decision["aggregate_joint_endpoint_target"][
        "off_diagonal_response_energy"
    ] is False
    assert decision["passed_complete_guard"] is False
    assert failed["passing_count"] == 207


def test_learned_verdict_is_suppressed_until_canary_reference_passes_4_of_4() -> None:
    invalid_reference = _passing_canary_reference_gate()
    invalid_reference["passed_4_of_4"] = False
    invalid_reference["passed_count"] = 3

    result = classify_learned_guard(
        _complete_learned_bank(),
        policies=POLICIES,
        profiles=PROFILES,
        deterministic_reference_gate=invalid_reference,
    )

    assert result["classification"] == "LEARNED-COMPLETE-GUARD-REFERENCE-INVALID"
    assert result["scientific_outcome"] == "NOT_TESTED"
    assert result["raw_guard_classification"] == (
        "R483-FROZEN-POLICIES-SOME-PASS-COMPLETE-GUARD"
    )
    assert result["checks"]["deterministic_reference_gate_4_of_4"] is False


def test_deterministic_tail_reuses_exact_four_of_four_phase1a_gate() -> None:
    contract = build_fresh()
    evaluation_profiles = tuple(
        profile["profile_id"]
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    )
    summaries: list[dict[str, object]] = []
    for profile_id in evaluation_profiles:
        summaries.append(
            _summary(profile_id=profile_id, arm_id=ZERO_ARM, seed=None)
        )
        summaries.append(
            _summary(
                profile_id=profile_id,
                arm_id=DETERMINISTIC_ARM,
                seed=None,
                common=1.02,
                peak=1.02,
                rocof=1.02,
            )
        )

    result = classify_deterministic_tail(
        summaries,
        contract=contract,
        expected_profiles=evaluation_profiles,
        bank_name="fresh",
    )
    assert result["classification"] == "DIRECT-MD-30S-FRESH-PASS"
    assert result["gate"]["passed_count"] == 4

    summaries[-1]["action_saturation_fraction"] = 0.06
    failed = classify_deterministic_tail(
        summaries,
        contract=contract,
        expected_profiles=evaluation_profiles,
        bank_name="fresh",
    )
    assert failed["classification"] == "DIRECT-MD-30S-FRESH-FAIL"
    assert failed["gate"]["passed_count"] == 3


def test_tail_factorial_is_complete_and_explicitly_not_pooled(monkeypatch) -> None:
    monkeypatch.setattr(r482_analysis, "SIGNFLIP_DRAWS", 1_000)
    seeds = tuple(range(501, 527))
    rows: list[dict[str, object]] = []
    for seed_index, seed in enumerate(seeds):
        actor_effect = 0.25 + seed_index * 0.00031
        critic_effect = 0.22 + seed_index * 0.00041
        interaction = -0.15 - seed_index * 0.00023
        critic_reward = 0.16 + seed_index * 0.00019
        for actor in ("N", "P"):
            for critic in ("N", "P"):
                for reward in (0, 1):
                    log_loss = (
                        1.0
                        + (actor == "P") * actor_effect
                        + (critic == "P") * critic_effect
                        + (actor == "P") * (critic == "P") * interaction
                        + (critic == "P") * reward * critic_reward
                    )
                    for profile_id in PROFILES:
                        row = _summary(
                            profile_id=profile_id,
                            arm_id=f"a{actor.lower()}_c{critic.lower()}_r{reward}",
                            seed=seed,
                        )
                        row.update(
                            {
                                "actor_source": actor,
                                "critic_source": critic,
                                "reward_access": reward,
                                "disturbance_differential_energy": math.exp(log_loss),
                            }
                        )
                        rows.append(row)

    result = analyse_tail_factorial(
        rows,
        expected_seeds=seeds,
        expected_profiles=PROFILES,
    )

    assert result["classification"] == "TAIL-MATERIAL-MAIN-EFFECT+TAIL-MATERIAL-INTERACTION"
    assert result["horizon_seconds"] == 30.0
    assert result["pooled_with_r483_six_second_primary"] is False
    assert result["substitutes_for_r483_primary"] is False
    assert len(result["seed_effects"]["actor_main"]) == 26
    json.dumps(result, sort_keys=True, allow_nan=False)


def test_global_classifier_suppresses_science_after_engineering_failure() -> None:
    child = {"classification": "PASS", "scientific_outcome": "PASS"}
    result = classify_r484(
        design_valid=True,
        missing_shards=["shard-15"],
        engineering_errors=[],
        integrity_errors=[],
        learned_guard=child,
        fresh_tail=child,
        canary_tail=child,
        tail_factorial=child,
    )
    assert result["classification"] == "ENGINEERING-INVALID"
    assert result["scientific_results_valid"] is False
    assert set(result["outcomes"].values()) == {"NOT_TESTED"}
