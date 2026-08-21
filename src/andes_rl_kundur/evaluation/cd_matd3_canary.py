"""Prospective Gate A canary contract and classifier for the fixed-title line.

This module is the frozen scientific contract for the fresh three-seed
development canary authorized by the R400 route amendment
(paper/yang_md_decoupling_marl/working/route_amendment_r400.md#gate-a).
It contains no ANDES import and no learning code.  The R401 evidence round
freezes every required input: the fresh development/evaluation banks,
50-Hz-controller-to-60-Hz reporting semantics, observation/action units, the
literal M/D decoder and readback, update/event timing, reward scaling,
interaction/tuning/checkpoint budgets, convergence and missing-run rules,
capacity reference, and the physical/no-harm estimators with the canary
decision tree.  The successor execution round must load this contract from
the R401 seal and may train exactly the three registered learning arms.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.md_decoupling_headroom import (
    DIFFERENTIAL_TRANSFORM,
    LOAD_IDS,
)

DEVICE_COUNT = 4
PAIR_KINDS = ("common", "differential", "localized")

ROUND_ID = "R401"
MANUSCRIPT_LINE = "yang-md-decoupling-marl"

LEARNING_ARM_IDS = (
    "yang_scalar_td3",
    "cd_matd3_no_message",
    "cd_matd3_message",
)
DETERMINISTIC_ARM_ID = "local_neighbour_md_km2_kd2"
TRAINING_SEEDS = (401, 402, 403)
BANK_SEED = 401

STEPS_PER_EPISODE = 30
DT_SECONDS = 0.2
EPISODES_PER_DEVELOPMENT_CYCLE = 24
DEVELOPMENT_CYCLES = 60
TOTAL_TRAINING_EPISODES = (
    EPISODES_PER_DEVELOPMENT_CYCLE * DEVELOPMENT_CYCLES
)
TOTAL_INTERACTION_STEPS = TOTAL_TRAINING_EPISODES * STEPS_PER_EPISODE

DETERMINISTIC_REFERENCE_ROLE = (
    "strong_evaluation_reference_no_training_budget"
)

_PROFILE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "canary_dev_a",
        "split": "development",
        "baseline_m0": [150.0, 250.0, 170.0, 230.0],
        "baseline_d0": [60.0, 140.0, 80.0, 120.0],
        "steady_loads": {"PQ_Bus14": 2.24, "PQ_Bus15": 0.42},
        "probe_magnitude": 0.85,
        "localized_location": "PQ_1",
        "localized_magnitude": 0.95,
    },
    {
        "profile_id": "canary_dev_b",
        "split": "development",
        "baseline_m0": [230.0, 150.0, 250.0, 170.0],
        "baseline_d0": [120.0, 60.0, 140.0, 80.0],
        "steady_loads": {"PQ_Bus14": 2.02, "PQ_Bus15": 0.66},
        "probe_magnitude": 1.05,
        "localized_location": "PQ_Bus15",
        "localized_magnitude": 1.15,
    },
    {
        "profile_id": "canary_dev_c",
        "split": "development",
        "baseline_m0": [210.0, 190.0, 160.0, 240.0],
        "baseline_d0": [130.0, 70.0, 110.0, 90.0],
        "steady_loads": {"PQ_Bus14": 2.42, "PQ_Bus15": 0.14},
        "probe_magnitude": 0.75,
        "localized_location": "PQ_0",
        "localized_magnitude": 0.85,
    },
    {
        "profile_id": "canary_dev_d",
        "split": "development",
        "baseline_m0": [240.0, 160.0, 190.0, 210.0],
        "baseline_d0": [90.0, 110.0, 70.0, 130.0],
        "steady_loads": {"PQ_Bus14": 2.12, "PQ_Bus15": 0.54},
        "probe_magnitude": 0.95,
        "localized_location": "PQ_Bus14",
        "localized_magnitude": 1.05,
    },
    {
        "profile_id": "canary_eval_a",
        "split": "evaluation",
        "baseline_m0": [140.0, 260.0, 200.0, 220.0],
        "baseline_d0": [50.0, 150.0, 90.0, 130.0],
        "steady_loads": {"PQ_Bus14": 2.56, "PQ_Bus15": 0.34},
        "probe_magnitude": 0.9,
        "localized_location": "PQ_0",
        "localized_magnitude": 1.0,
    },
    {
        "profile_id": "canary_eval_b",
        "split": "evaluation",
        "baseline_m0": [260.0, 140.0, 220.0, 200.0],
        "baseline_d0": [150.0, 50.0, 130.0, 90.0],
        "steady_loads": {"PQ_Bus14": 2.06, "PQ_Bus15": 0.26},
        "probe_magnitude": 0.8,
        "localized_location": "PQ_Bus14",
        "localized_magnitude": 0.9,
    },
    {
        "profile_id": "canary_eval_c",
        "split": "evaluation",
        "baseline_m0": [180.0, 240.0, 150.0, 210.0],
        "baseline_d0": [70.0, 130.0, 60.0, 110.0],
        "steady_loads": {"PQ_Bus14": 1.96, "PQ_Bus15": 0.64},
        "probe_magnitude": 1.0,
        "localized_location": "PQ_Bus15",
        "localized_magnitude": 1.1,
    },
    {
        "profile_id": "canary_eval_d",
        "split": "evaluation",
        "baseline_m0": [220.0, 200.0, 260.0, 140.0],
        "baseline_d0": [110.0, 90.0, 150.0, 50.0],
        "steady_loads": {"PQ_Bus14": 2.32, "PQ_Bus15": 0.46},
        "probe_magnitude": 1.1,
        "localized_location": "PQ_1",
        "localized_magnitude": 1.2,
    },
)


def _signed_scenarios(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    profile_id = str(profile["profile_id"])
    probe = float(profile["probe_magnitude"])
    localized = float(profile["localized_magnitude"])
    location = str(profile["localized_location"])
    common = {load_id: probe / 4.0 for load_id in LOAD_IDS}
    differential = {
        "PQ_0": probe / 4.0,
        "PQ_1": probe / 4.0,
        "PQ_Bus14": -probe / 4.0,
        "PQ_Bus15": -probe / 4.0,
    }
    bases = {
        "common": (probe, common),
        "differential": (probe, differential),
        "localized": (localized, {location: localized}),
    }
    scenarios: list[dict[str, Any]] = []
    for pair_kind in PAIR_KINDS:
        magnitude, positive = bases[pair_kind]
        for sign, multiplier in (("positive", 1.0), ("negative", -1.0)):
            scenarios.append(
                {
                    "scenario_id": f"{profile_id}_{pair_kind}_{sign}",
                    "profile_id": profile_id,
                    "pair_kind": pair_kind,
                    "sign": sign,
                    "magnitude": magnitude,
                    "delta_u": {
                        key: multiplier * float(value)
                        for key, value in positive.items()
                    },
                }
            )
    return scenarios


def build_contract() -> dict[str, Any]:
    """Return the immutable JSON-compatible Gate A canary contract."""

    profiles = []
    for source in _PROFILE_ROWS:
        profile = dict(source)
        profile["steady_loads"] = dict(source["steady_loads"])
        profile["scenarios"] = _signed_scenarios(profile)
        profiles.append(profile)
    development_scenario_order = [
        f"{profile['profile_id']}_{pair_kind}_{sign}"
        for profile in profiles
        if profile["split"] == "development"
        for pair_kind in PAIR_KINDS
        for sign in ("positive", "negative")
    ]
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": MANUSCRIPT_LINE,
        "stage": "gate-a-three-seed-development-canary-contract",
        "authority": (
            "paper/yang_md_decoupling_marl/working/"
            "route_amendment_r400.md#gate-a----fresh-three-seed-development-canary"
        ),
        "steps": STEPS_PER_EPISODE,
        "dt_seconds": DT_SECONDS,
        "bank_seed": BANK_SEED,
        "physical_nominal_frequency_hz": 60.0,
        "control_nominal_frequency_hz": 50.0,
        "frequency_semantics": (
            "physical endpoints use the installed ANDES 60-Hz base; the V4 "
            "controller slots remain on the protected legacy 50-Hz scale and "
            "are converted once by adapt_v4_observations_to_physical "
            "(slots 1..6 multiplied by 60/50) before any 60-Hz consumer"
        ),
        "differential_transform": DIFFERENTIAL_TRANSFORM.tolist(),
        "action_bounds": [-1.0, 1.0],
        "action_slew_limit": 0.25,
        "decoder": {
            "delta_m_negative": -200.0,
            "delta_m_positive": 600.0,
            "delta_d_negative": -200.0,
            "delta_d_positive": 600.0,
            "m_lower_clamp": 20.0,
            "d_lower_clamp": 10.0,
            "mapping_atol": 3.0517578125e-05,
        },
        "observation_contract": {
            "local_actor_slots": [0, 1, 2],
            "neighbour_frequency_slots": [3, 4],
            "neighbour_rocof_slots": [5, 6],
            "slot_units": [
                "active_power_pu_over_2",
                "frequency_deviation_over_3",
                "rocof_over_5",
                "neighbour_frequency_deviation_over_3",
                "neighbour_frequency_deviation_over_3",
                "neighbour_rocof_over_5",
                "neighbour_rocof_over_5",
            ],
            "message_arm_runtime_input": "full 7-slot V4 row",
            "no_message_arm_runtime_input": (
                "identical 7-slot network input with slots 3..6 zeroed "
                "by the env adapter at every step"
            ),
            "joint_critic_input": (
                "concatenated 4 x 7 observation rows plus 4 x 2 actions "
                "for every arm; training-only, never at runtime"
            ),
        },
        "reward_contract": {
            "scalar_td3": {
                "kind": "yang_compatible_scalar_reward_v4_defaults",
                "phi_f": 100.0,
                "phi_abs": 50.0,
                "phi_h": 0.0056,
                "phi_d": 0.0056,
                "reward_scale": "50-Hz controller base",
                "step_reward": "sum over the four agents of the V4 per-agent rewards",
                "tds_failure_step_reward": -200.0,
            },
            "cd_matd3": {
                "kind": "two_component_common_differential_costs",
                "sigma_f_hz": 0.15,
                "sigma_p_pu": 0.25,
                "sigma_rocof_hz_s": 1.0,
                "differential_cost": (
                    "sum_k (z_d,k / sigma_f)^2 / 3 + "
                    "sum_k (p_d,k / sigma_p)^2 / 3 with "
                    "z_d = T_d (f - 60) and p_d = T_d P_es"
                ),
                "common_cost": (
                    "mean_i ((f_i - 60) / sigma_f)^2 + "
                    "mean_i (RoCoF_i / sigma_rocof)^2"
                ),
                "tds_failure_costs": {"common": 50.0, "differential": 50.0},
                "lagrange_initial": 1.0,
                "lagrange_maximum": 10.0,
                "lagrange_step": 0.05,
                "common_budget_per_episode": 3.0,
                "multiplier_update": (
                    "after each episode: lambda = clip(lambda + 0.05 * "
                    "(sum_t c_c(t) - 3.0), 0.0, 10.0)"
                ),
                "actor_objective": (
                    "minimize -(Q_differential + lambda * Q_common)"
                ),
            },
            "reward_used_for_gate": False,
        },
        "learner_contract": {
            "actor": {
                "input_dim": 7,
                "output_dim": 2,
                "hidden_sizes": [256, 256],
                "output": "tanh",
            },
            "critic": {
                "input_dim": 4 * 7 + 4 * 2,
                "output_dim": 2,
                "hidden_sizes": [256, 256],
                "twin": True,
            },
            "scalar_td3_critic_output_dim": 1,
            "scalar_td3_critic_scope": (
                "joint centralized critic over all four observation rows "
                "and actions; training-only"
            ),
            "lr": 3e-4,
            "gamma": 0.99,
            "tau": 0.005,
            "buffer_size": 200000,
            "batch_size": 256,
            "policy_noise": 0.2,
            "noise_clip": 0.5,
            "explore_noise": 0.1,
            "policy_delay": 2,
            "update_schedule": (
                "critic update every step after the buffer holds at least "
                "batch_size transitions; actor and target updates every "
                "policy_delay critic updates"
            ),
            "evaluation_policy": "deterministic (no exploration noise)",
        },
        "training_contract": {
            "development_scenario_order": development_scenario_order,
            "episode_schedule": (
                "episode e uses development_scenario_order[e mod 24]; "
                "60 full cycles; identical for every arm and seed"
            ),
            "total_training_episodes": TOTAL_TRAINING_EPISODES,
            "total_interaction_steps": TOTAL_INTERACTION_STEPS,
            "convergence_rule": (
                "fixed interaction budget, no early stopping; convergence "
                "diagnostics (episode returns, critic losses, lambda) are "
                "recorded but never used for selection"
            ),
            "invalid_run_condition": (
                "nonfinite critic loss or nonfinite action at any step "
                "marks the run invalid, which consumes the seed"
            ),
            "checkpoint_rule": (
                "final weights only for evaluation; weights snapshots "
                "saved every 240 episodes for provenance; no best-of selection"
            ),
            "evaluation_access": (
                "no evaluation-profile execution during training; evaluation "
                "runs only after all nine trainings complete"
            ),
        },
        "missing_run_rules": {
            "restart_quota_per_arm_seed": 1,
            "restart_condition": (
                "host-side crash signature only (process killed, memory "
                "exhaustion, WSL halt); a restart trains from scratch with "
                "the same seed"
            ),
            "missing_seed_after_quota": "CANARY-INVALID",
            "evaluation_retry": (
                "never; any missing or corrupt evaluation record is "
                "CANARY-INVALID"
            ),
        },
        "thresholds": {
            "maximum_common_harm": 0.03,
            "maximum_action_stress_harm": 0.10,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "independent_action_dispersion_floor": 1.0e-6,
        },
        "profiles": profiles,
        "learning_arm_ids": list(LEARNING_ARM_IDS),
        "deterministic_arm_id": DETERMINISTIC_ARM_ID,
        "deterministic_reference_role": DETERMINISTIC_REFERENCE_ROLE,
        "training_seeds": list(TRAINING_SEEDS),
        "selection_unit": "training_seed",
        "uncertainty": (
            "three-seed median plus seed-level table; descriptive, not "
            "population inference"
        ),
        "capacity_reference": "memory/rounds/R401/capacity_evidence.json",
        "evaluation_record_keys": (
            "profile_id, arm_id, training_seed (null for deterministic), "
            "scenario_id, steps, identity, initial_freq_hz_physical, "
            "checkpoint_sha256 (learning arms only)"
        ),
        "canary_outcomes": [
            "CANARY-PASS",
            "CANARY-FAIL",
            "CANARY-INVALID",
        ],
    }


def contract_sha256(contract: Mapping[str, Any] | None = None) -> str:
    """Return the canonical payload hash of the frozen contract."""

    payload = build_contract() if contract is None else contract
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _aggregate(rows: Sequence[Mapping[str, Any]], key: str) -> float:
    return float(sum(float(row[key]) for row in rows))


def _not_harmed(value: float, reference: float, fraction: float) -> bool:
    return bool(value <= (1.0 + fraction) * reference + 1.0e-15)


def _common_guard(
    candidate: Mapping[str, Any],
    reference: Mapping[str, Any],
    *,
    maximum_harm: float,
) -> dict[str, bool]:
    return {
        "common_frequency_no_harm": _not_harmed(
            float(candidate["common_frequency_iae_hz_s"]),
            float(reference["common_frequency_iae_hz_s"]),
            maximum_harm,
        ),
        "worst_peak_no_harm": _not_harmed(
            float(candidate["worst_unit_peak_hz"]),
            float(reference["worst_unit_peak_hz"]),
            maximum_harm,
        ),
        "rocof_no_harm": _not_harmed(
            float(candidate["worst_rocof_hz_s"]),
            float(reference["worst_rocof_hz_s"]),
            maximum_harm,
        ),
    }


def _stress_guard(
    candidate: Mapping[str, Any],
    reference: Mapping[str, Any],
    *,
    maximum_harm: float,
) -> dict[str, bool]:
    return {
        "action_rms_no_harm": _not_harmed(
            float(candidate["action_rms"]),
            float(reference["action_rms"]),
            maximum_harm,
        ),
        "action_variation_no_harm": _not_harmed(
            float(candidate["action_total_variation"]),
            float(reference["action_total_variation"]),
            maximum_harm,
        ),
    }


def _invalid(
    checks: Mapping[str, Any],
    *,
    classification: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": MANUSCRIPT_LINE,
        "classification": classification,
        "checks": dict(checks),
        "training_authorized": False,
        "claim_scope": "frozen fresh heterogeneous bank only",
    }
    if extra:
        result.update(extra)
    return result


def classify_canary(
    training_manifests: Sequence[Mapping[str, Any]],
    evaluation_summaries: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one complete canary bank from manifests and summaries.

    Summary rows come from the frozen R399 profile estimators computed per
    evaluation profile per arm per seed, plus deterministic reference rows
    with training_seed null.  Training manifests describe interaction,
    checkpoint, convergence-diagnostic, and restart facts per arm-seed.
    No reward or coordinate score may influence the classification.
    """

    spec = build_contract() if contract is None else contract
    thresholds = spec["thresholds"]
    arm_ids = [str(value) for value in spec["learning_arm_ids"]]
    seeds = [int(value) for value in spec["training_seeds"]]
    deterministic_arm = str(spec["deterministic_arm_id"])
    evaluation_ids = [
        str(profile["profile_id"])
        for profile in spec["profiles"]
        if profile["split"] == "evaluation"
    ]

    checks: dict[str, Any] = {
        "complete_bank": False,
        "all_rows_valid": False,
        "all_manifests_valid": False,
        "reward_unused": spec["reward_contract"]["reward_used_for_gate"] is False,
        "budget_frozen": spec["training_contract"][
            "total_interaction_steps"
        ]
        == TOTAL_INTERACTION_STEPS,
    }

    expected_keys = {
        (profile_id, arm_id, seed)
        for profile_id in evaluation_ids
        for arm_id in [*arm_ids, deterministic_arm]
        for seed in ([None] if arm_id == deterministic_arm else seeds)
    }
    by_key: dict[tuple[str, str, int | None], Mapping[str, Any]] = {}
    duplicates = False
    for summary in evaluation_summaries:
        profile_id = str(summary.get("profile_id", ""))
        arm_id = str(summary.get("arm_id", ""))
        seed_raw = summary.get("training_seed", None)
        seed = None if seed_raw is None else int(seed_raw)
        key = (profile_id, arm_id, seed)
        if key in by_key:
            duplicates = True
        by_key[key] = summary

    manifests: dict[tuple[str, int], Mapping[str, Any]] = {}
    manifest_duplicates = False
    for manifest in training_manifests:
        arm_id = str(manifest.get("arm_id", ""))
        seed = int(manifest.get("training_seed", -1))
        key = (arm_id, seed)
        if key in manifests:
            manifest_duplicates = True
        manifests[key] = manifest
    expected_manifests = {(arm_id, seed) for arm_id in arm_ids for seed in seeds}
    checks["complete_bank"] = bool(
        not duplicates and set(by_key) == expected_keys
    )
    checks["all_manifests_valid"] = bool(
        not manifest_duplicates
        and set(manifests) == expected_manifests
        and all(
            int(manifests[key].get("interaction_steps", -1))
            == TOTAL_INTERACTION_STEPS
            and bool(manifests[key].get("convergence_diagnostics_valid")) is True
            and bool(manifests[key].get("missing")) is False
            and int(manifests[key].get("restart_count", -1))
            <= int(spec["missing_run_rules"]["restart_quota_per_arm_seed"])
            for key in expected_manifests
        )
    )
    checks["all_rows_valid"] = bool(
        checks["complete_bank"]
        and all(
            bool(summary.get("valid")) is True
            and bool(summary.get("actuator_mapping_pass")) is True
            and bool(summary.get("action_bound_violation")) is False
            and bool(summary.get("action_slew_violation")) is False
            for summary in by_key.values()
        )
    )
    if not all(
        checks[name]
        for name in ("complete_bank", "all_manifests_valid", "all_rows_valid")
    ):
        return _invalid(checks, classification="CANARY-INVALID")

    maximum_common_harm = float(thresholds["maximum_common_harm"])
    maximum_stress_harm = float(thresholds["maximum_action_stress_harm"])
    maximum_saturation = float(
        thresholds["maximum_action_saturation_fraction"]
    )
    variation_floor = float(
        thresholds["nonconstant_action_variation_floor"]
    )
    dispersion_floor = float(
        thresholds["independent_action_dispersion_floor"]
    )

    guard_failures: list[dict[str, Any]] = []
    for profile_id in evaluation_ids:
        reference = by_key[(profile_id, deterministic_arm, None)]
        for arm_id in arm_ids:
            for seed in seeds:
                row = by_key[(profile_id, arm_id, seed)]
                guard = {
                    **_common_guard(
                        row, reference, maximum_harm=maximum_common_harm
                    ),
                    **_stress_guard(
                        row, reference, maximum_harm=maximum_stress_harm
                    ),
                    "saturation_budget": float(
                        row["action_saturation_fraction"]
                    )
                    <= maximum_saturation,
                    "nonconstant_action": float(
                        row["minimum_record_total_variation"]
                    )
                    > variation_floor,
                    "independent_per_vsg_action": float(
                        row["minimum_record_action_row_dispersion"]
                    )
                    > dispersion_floor,
                }
                if not all(guard.values()):
                    guard_failures.append(
                        {
                            "profile_id": profile_id,
                            "arm_id": arm_id,
                            "training_seed": seed,
                            "failed": [
                                name
                                for name, value in guard.items()
                                if not value
                            ],
                        }
                    )
    checks["all_no_harm_and_action_guards"] = not guard_failures
    if guard_failures:
        return _invalid(
            checks,
            classification="CANARY-FAIL",
            extra={"guard_failures": guard_failures},
        )

    endpoints = ("off_diagonal_response_energy", "disturbance_differential_energy")

    def arm_endpoint(arm_id: str, seed: int | None, endpoint: str) -> float:
        return _aggregate(
            [
                by_key[(profile_id, arm_id, seed)]
                for profile_id in evaluation_ids
            ],
            endpoint,
        )

    deterministic = {
        endpoint: arm_endpoint(deterministic_arm, None, endpoint)
        for endpoint in endpoints
    }
    per_seed: dict[tuple[str, int], dict[str, float]] = {
        (arm_id, seed): {
            endpoint: arm_endpoint(arm_id, seed, endpoint)
            for endpoint in endpoints
        }
        for arm_id in arm_ids
        for seed in seeds
    }
    full_arm = str(spec["learning_arm_ids"][2])
    comparators = [str(value) for value in spec["learning_arm_ids"][:2]]

    seed_improvements: dict[str, Any] = {}
    median_improvements: dict[str, Any] = {}
    two_of_three: dict[str, Any] = {}
    for comparator in comparators:
        per_endpoint: dict[str, dict[str, float]] = {e: {} for e in endpoints}
        for seed in seeds:
            for endpoint in endpoints:
                base = per_seed[(comparator, seed)][endpoint]
                per_endpoint[endpoint][seed] = (
                    base - per_seed[(full_arm, seed)][endpoint]
                ) / base
        median_improvements[comparator] = {
            endpoint: float(
                np.median([per_endpoint[endpoint][s] for s in seeds])
            )
            for endpoint in endpoints
        }
        seed_improvements[comparator] = {
            "seed_values": {
                seed: {
                    endpoint: per_endpoint[endpoint][seed]
                    for endpoint in endpoints
                }
                for seed in seeds
            }
        }
        two_of_three[comparator] = {
            endpoint: sum(
                1
                for seed in seeds
                if per_endpoint[endpoint][seed] > 0.0
            )
            >= 2
            for endpoint in endpoints
        }

    median_pass_vs_comparators = all(
        all(
            median_improvements[comparator][endpoint] > 0.0
            for endpoint in endpoints
        )
        for comparator in comparators
    )
    two_of_three_pass = all(
        all(two_of_three[comparator].values()) for comparator in comparators
    )
    full_medians = {
        endpoint: float(
            np.median(
                [per_seed[(full_arm, seed)][endpoint] for seed in seeds]
            )
        )
        for endpoint in endpoints
    }
    deterministic_favorable = {
        endpoint: full_medians[endpoint] < deterministic[endpoint]
        for endpoint in endpoints
    }
    deterministic_pass = all(deterministic_favorable.values())

    canary = {
        "passed": bool(
            median_pass_vs_comparators
            and two_of_three_pass
            and deterministic_pass
        ),
        "full_arm": full_arm,
        "comparators": comparators,
        "deterministic_arm": deterministic_arm,
        "deterministic_endpoints": deterministic,
        "full_method_seed_median_endpoints": full_medians,
        "per_seed_endpoints": {
            f"{arm_id}_s{seed}": per_seed[(arm_id, seed)]
            for arm_id in arm_ids
            for seed in seeds
        },
        "median_improvement_vs_comparators": median_improvements,
        "two_of_three_seeds_improve": two_of_three,
        "deterministic_reference_favorable": deterministic_favorable,
        "guard_failures": guard_failures,
    }
    checks["positive_reference_energies"] = all(
        deterministic[endpoint] > 0.0 for endpoint in endpoints
    ) and all(
        per_seed[key][endpoint] > 0.0
        for key in per_seed
        for endpoint in endpoints
    )
    if not checks["positive_reference_energies"]:
        return _invalid(
            checks,
            classification="CANARY-INVALID",
            extra={"canary": canary},
        )
    classification = "CANARY-PASS" if canary["passed"] else "CANARY-FAIL"
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": MANUSCRIPT_LINE,
        "classification": classification,
        "checks": checks,
        "canary": canary,
        "training_authorized": False,
        "reward_used_for_gate": spec["reward_contract"]["reward_used_for_gate"],
        "pass_authorizes": (
            "only a separately planned and sealed Gate B five-seed held-out "
            "comparison; a pass is not title evidence"
        ),
        "fail_consequence": (
            "ends the selected learner route without algorithm replacement"
        ),
        "claim_scope": "frozen fresh heterogeneous bank only",
    }


def evaluation_record_count(contract: Mapping[str, Any] | None = None) -> int:
    """Return the complete evaluation record count (24 per arm-seed)."""

    spec = build_contract() if contract is None else contract
    evaluation_scenarios = sum(
        len(profile["scenarios"])
        for profile in spec["profiles"]
        if profile["split"] == "evaluation"
    )
    return evaluation_scenarios * (len(spec["learning_arm_ids"]) * len(
        spec["training_seeds"]
    ) + 1)


def training_run_count(contract: Mapping[str, Any] | None = None) -> int:
    """Return the number of registered arm-seed training runs (9)."""

    spec = build_contract() if contract is None else contract
    return len(spec["learning_arm_ids"]) * len(spec["training_seeds"])


__all__ = [
    "BANK_SEED",
    "DETERMINISTIC_ARM_ID",
    "LEARNING_ARM_IDS",
    "TOTAL_INTERACTION_STEPS",
    "TOTAL_TRAINING_EPISODES",
    "TRAINING_SEEDS",
    "build_contract",
    "classify_canary",
    "contract_sha256",
    "evaluation_record_count",
    "training_run_count",
]
