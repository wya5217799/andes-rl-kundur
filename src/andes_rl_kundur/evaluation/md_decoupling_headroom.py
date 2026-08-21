"""Pure joint-headroom contract and classifier for the Yang-compatible line.

This module contains no ANDES import and no learning code.  It owns the frozen
finite-bank contract, converts completed physical traces into profile-level
endpoints, and classifies only a complete development/evaluation bank.  The
R399 WSL runner owns physical execution and provenance.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.per_vsg_md import local_neighbour_md_candidates

DEVICE_COUNT = 4
PAIR_KINDS = ("common", "differential", "localized")
DIFFERENTIAL_TRANSFORM = np.asarray(
    [
        [0.5, 0.5, -0.5, -0.5],
        [1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0), 0.0, 0.0],
        [0.0, 0.0, 1.0 / np.sqrt(2.0), -1.0 / np.sqrt(2.0)],
    ],
    dtype=float,
)
LOAD_IDS = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")


_PROFILE_ROWS: tuple[dict[str, Any], ...] = (
    {
        "profile_id": "dev_a",
        "split": "development",
        "baseline_m0": [160.0, 240.0, 180.0, 220.0],
        "baseline_d0": [70.0, 130.0, 90.0, 110.0],
        "steady_loads": {"PQ_Bus14": 2.28, "PQ_Bus15": 0.20},
        "probe_magnitude": 0.8,
        "localized_location": "PQ_0",
        "localized_magnitude": 0.9,
    },
    {
        "profile_id": "dev_b",
        "split": "development",
        "baseline_m0": [220.0, 180.0, 240.0, 160.0],
        "baseline_d0": [110.0, 90.0, 130.0, 70.0],
        "steady_loads": {"PQ_Bus14": 2.08, "PQ_Bus15": 0.60},
        "probe_magnitude": 1.0,
        "localized_location": "PQ_Bus14",
        "localized_magnitude": 1.1,
    },
    {
        "profile_id": "eval_a",
        "split": "evaluation",
        "baseline_m0": [150.0, 250.0, 190.0, 210.0],
        "baseline_d0": [60.0, 140.0, 80.0, 120.0],
        "steady_loads": {"PQ_Bus14": 2.48, "PQ_Bus15": 0.30},
        "probe_magnitude": 0.9,
        "localized_location": "PQ_1",
        "localized_magnitude": 1.0,
    },
    {
        "profile_id": "eval_b",
        "split": "evaluation",
        "baseline_m0": [250.0, 150.0, 210.0, 190.0],
        "baseline_d0": [140.0, 60.0, 120.0, 80.0],
        "steady_loads": {"PQ_Bus14": 2.18, "PQ_Bus15": 0.10},
        "probe_magnitude": 0.7,
        "localized_location": "PQ_Bus15",
        "localized_magnitude": 0.8,
    },
    {
        "profile_id": "eval_c",
        "split": "evaluation",
        "baseline_m0": [170.0, 230.0, 250.0, 150.0],
        "baseline_d0": [75.0, 125.0, 145.0, 55.0],
        "steady_loads": {"PQ_Bus14": 1.88, "PQ_Bus15": 0.60},
        "probe_magnitude": 1.1,
        "localized_location": "PQ_0",
        "localized_magnitude": 1.2,
    },
    {
        "profile_id": "eval_d",
        "split": "evaluation",
        "baseline_m0": [230.0, 170.0, 150.0, 250.0],
        "baseline_d0": [125.0, 75.0, 55.0, 145.0],
        "steady_loads": {"PQ_Bus14": 2.38, "PQ_Bus15": 0.30},
        "probe_magnitude": 0.8,
        "localized_location": "PQ_Bus14",
        "localized_magnitude": 0.9,
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
    """Return the immutable JSON-compatible R399 scientific contract."""

    profiles = []
    for source in _PROFILE_ROWS:
        profile = dict(source)
        profile["steady_loads"] = dict(source["steady_loads"])
        profile["scenarios"] = _signed_scenarios(profile)
        profiles.append(profile)
    candidate_ids = [row.name for row in local_neighbour_md_candidates()]
    return {
        "schema_version": 1,
        "round": "R399",
        "manuscript_line": "yang-md-decoupling-marl",
        "steps": 30,
        "dt_seconds": 0.2,
        "seed": 399,
        "physical_nominal_frequency_hz": 60.0,
        "control_nominal_frequency_hz": 50.0,
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
        "thresholds": {
            "minimum_joint_improvement": 0.05,
            "maximum_common_harm": 0.03,
            "maximum_action_stress_harm": 0.10,
            "maximum_action_saturation_fraction": 0.05,
            "nonconstant_action_variation_floor": 1.0e-6,
            "independent_action_dispersion_floor": 1.0e-6,
        },
        "profiles": profiles,
        "candidate_arm_ids": candidate_ids,
        "arm_ids": ["zero", *candidate_ids],
        "oracle_role": "non_deployable_outcome_selector_per_evaluation_profile",
        "selection_unit": "heterogeneity_profile",
        "uncertainty": "evaluation_profile_table_plus_leave_one_profile_out_range",
        "reward_used_for_gate": False,
        "training_authorized": False,
    }


def _finite_array(value: object, shape: tuple[int, ...], name: str) -> np.ndarray:
    array = np.asarray(value, dtype=float)
    if array.shape != shape or not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must be finite with shape {shape}")
    return array


def _profile_by_id(contract: Mapping[str, Any], profile_id: str) -> Mapping[str, Any]:
    matches = [
        profile
        for profile in contract["profiles"]
        if str(profile["profile_id"]) == profile_id
    ]
    if len(matches) != 1:
        raise ValueError(f"unknown or duplicate profile: {profile_id}")
    return matches[0]


def _record_arrays(
    record: Mapping[str, Any],
    *,
    contract: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    expected_steps = int(contract["steps"])
    steps = record.get("steps")
    if not isinstance(steps, list) or len(steps) != expected_steps:
        raise ValueError("record must contain the expected number of steps")
    if record.get("completed") is not True or record.get("tds_failed") is not False:
        raise ValueError("record is incomplete or has a TDS failure")
    frequencies = np.stack(
        [
            _finite_array(step.get("freq_hz_physical"), (4,), "frequency")
            for step in steps
        ]
    )
    actions = np.stack(
        [_finite_array(step.get("action_norm"), (4, 2), "action") for step in steps]
    )
    delta_m = np.stack(
        [_finite_array(step.get("delta_M"), (4,), "delta M") for step in steps]
    )
    delta_d = np.stack(
        [_finite_array(step.get("delta_D"), (4,), "delta D") for step in steps]
    )
    actual_m = np.stack(
        [_finite_array(step.get("M_es"), (4,), "executed M") for step in steps]
    )
    actual_d = np.stack(
        [_finite_array(step.get("D_es"), (4,), "executed D") for step in steps]
    )
    initial = _finite_array(
        record.get("initial_freq_hz_physical"), (4,), "initial frequency"
    )
    identity = record.get("identity")
    if not isinstance(identity, Mapping):
        raise ValueError("record must contain actuator identity")
    baseline_m = _finite_array(identity.get("baseline_m0"), (4,), "baseline M")
    baseline_d = _finite_array(identity.get("baseline_d0"), (4,), "baseline D")
    decoder = contract["decoder"]
    expected_delta_m = np.where(
        actions[:, :, 0] >= 0.0,
        actions[:, :, 0] * float(decoder["delta_m_positive"]),
        actions[:, :, 0] * -float(decoder["delta_m_negative"]),
    )
    expected_delta_d = np.where(
        actions[:, :, 1] >= 0.0,
        actions[:, :, 1] * float(decoder["delta_d_positive"]),
        actions[:, :, 1] * -float(decoder["delta_d_negative"]),
    )
    expected_m = np.maximum(
        baseline_m[None, :] + expected_delta_m,
        float(decoder["m_lower_clamp"]),
    )
    expected_d = np.maximum(
        baseline_d[None, :] + expected_delta_d,
        float(decoder["d_lower_clamp"]),
    )
    atol = float(decoder["mapping_atol"])
    mapping = np.asarray(
        [
            np.allclose(delta_m, expected_delta_m, rtol=0.0, atol=atol),
            np.allclose(delta_d, expected_delta_d, rtol=0.0, atol=atol),
            np.allclose(actual_m, expected_m, rtol=0.0, atol=atol),
            np.allclose(actual_d, expected_d, rtol=0.0, atol=atol),
        ],
        dtype=bool,
    )
    return {
        "frequencies": frequencies,
        "actions": actions,
        "initial_frequency": initial,
        "mapping": mapping,
    }


def _settling_time(differential_response: np.ndarray, *, dt: float) -> float:
    norms = np.linalg.norm(differential_response, axis=1)
    peak = float(np.max(norms))
    if peak == 0.0:
        return 0.0
    limit = 0.02 * peak
    for index in range(norms.size):
        if np.all(norms[index:] <= limit):
            return float((index + 1) * dt)
    return float(norms.size * dt)


def summarise_profile(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarise one complete six-scenario profile-arm physical block."""

    spec = build_contract() if contract is None else contract
    if len(records) != 6:
        raise ValueError("profile summary requires exactly six records")
    profile_ids = {str(record.get("profile_id", "")) for record in records}
    arm_ids = {str(record.get("arm_id", "")) for record in records}
    if len(profile_ids) != 1 or len(arm_ids) != 1:
        raise ValueError("records must share exactly one profile and arm")
    profile_id = next(iter(profile_ids))
    arm_id = next(iter(arm_ids))
    profile = _profile_by_id(spec, profile_id)
    expected = {
        str(scenario["scenario_id"]): scenario for scenario in profile["scenarios"]
    }
    by_scenario: dict[str, Mapping[str, Any]] = {}
    arrays: dict[str, dict[str, np.ndarray]] = {}
    for record in records:
        scenario_id = str(record.get("scenario_id", ""))
        if scenario_id in by_scenario or scenario_id not in expected:
            raise ValueError("duplicate or unregistered scenario record")
        scenario = expected[scenario_id]
        for key in ("profile_id", "pair_kind", "sign"):
            if str(record.get(key, "")) != str(scenario[key]):
                raise ValueError(f"scenario metadata mismatch for {key}")
        if not np.isclose(
            float(record.get("magnitude", np.nan)),
            float(scenario["magnitude"]),
            rtol=0.0,
            atol=0.0,
        ):
            raise ValueError("scenario magnitude mismatch")
        by_scenario[scenario_id] = record
        arrays[scenario_id] = _record_arrays(record, contract=spec)
    if set(by_scenario) != set(expected):
        raise ValueError("profile scenario bank is incomplete")

    nominal = float(spec["physical_nominal_frequency_hz"])
    transform = _finite_array(
        spec["differential_transform"], (3, 4), "differential transform"
    )
    dt = float(spec["dt_seconds"])
    pair_responses: dict[str, dict[str, np.ndarray | float]] = {}
    for pair_kind in PAIR_KINDS:
        positive_id = f"{profile_id}_{pair_kind}_positive"
        negative_id = f"{profile_id}_{pair_kind}_negative"
        positive = arrays[positive_id]["frequencies"] - nominal
        negative = arrays[negative_id]["frequencies"] - nominal
        odd = 0.5 * (positive - negative)
        common = np.mean(odd, axis=1)
        differential = odd @ transform.T
        magnitude = float(expected[positive_id]["magnitude"])
        pair_responses[pair_kind] = {
            "common": common,
            "differential": differential,
            "magnitude": magnitude,
        }

    common_pair = pair_responses["common"]
    differential_pair = pair_responses["differential"]
    off_diagonal = (
        float(np.sum(np.mean(np.asarray(common_pair["differential"]) ** 2, axis=1)))
        * dt
        / float(common_pair["magnitude"]) ** 2
        + float(np.sum(np.asarray(differential_pair["common"]) ** 2))
        * dt
        / float(differential_pair["magnitude"]) ** 2
    )
    differential_energy = sum(
        float(
            np.sum(
                np.mean(np.asarray(pair_responses[kind]["differential"]) ** 2, axis=1)
            )
        )
        * dt
        / float(pair_responses[kind]["magnitude"]) ** 2
        for kind in PAIR_KINDS
    )

    all_frequencies = [value["frequencies"] for value in arrays.values()]
    common_iae = sum(
        float(np.sum(np.abs(np.mean(frequencies - nominal, axis=1))) * dt)
        for frequencies in all_frequencies
    )
    worst_peak = max(
        float(np.max(np.abs(frequencies - nominal)))
        for frequencies in all_frequencies
    )
    worst_rocof = max(
        float(
            np.max(
                np.abs(
                    np.diff(
                        np.concatenate(
                            [value["initial_frequency"][None, :], value["frequencies"]],
                            axis=0,
                        ),
                        axis=0,
                    )
                    / dt
                )
            )
        )
        for value in arrays.values()
    )

    action_blocks = [value["actions"] for value in arrays.values()]
    all_actions = np.stack(action_blocks)
    record_differences = [
        np.diff(
            np.concatenate([np.zeros((1, 4, 2)), actions], axis=0),
            axis=0,
        )
        for actions in action_blocks
    ]
    record_variations = [
        float(np.sum(np.mean(np.abs(differences), axis=(1, 2))))
        for differences in record_differences
    ]
    record_dispersions = [
        float(np.max(np.ptp(actions, axis=1))) for actions in action_blocks
    ]
    lower, upper = (float(value) for value in spec["action_bounds"])
    tolerance = 1.0e-9
    saturation = np.logical_or(
        all_actions <= lower + tolerance,
        all_actions >= upper - tolerance,
    )
    mapping_pass = all(bool(np.all(value["mapping"])) for value in arrays.values())
    bound_violation = bool(
        np.any(all_actions < lower - tolerance) or np.any(all_actions > upper + tolerance)
    )
    slew_violation = any(
        bool(
            np.any(
                np.abs(differences)
                > float(spec["action_slew_limit"]) + tolerance
            )
        )
        for differences in record_differences
    )
    numeric = np.asarray(
        [off_diagonal, differential_energy, common_iae, worst_peak, worst_rocof],
        dtype=float,
    )
    return {
        "profile_id": profile_id,
        "split": str(profile["split"]),
        "arm_id": arm_id,
        "valid": bool(
            np.all(np.isfinite(numeric))
            and np.all(numeric >= 0.0)
            and mapping_pass
            and not bound_violation
            and not slew_violation
        ),
        "record_count": len(records),
        "off_diagonal_response_energy": off_diagonal,
        "disturbance_differential_energy": differential_energy,
        "common_frequency_iae_hz_s": common_iae,
        "worst_unit_peak_hz": worst_peak,
        "worst_rocof_hz_s": worst_rocof,
        "differential_settling_seconds": {
            kind: _settling_time(
                np.asarray(pair_responses[kind]["differential"]), dt=dt
            )
            for kind in PAIR_KINDS
        },
        "action_rms": float(np.sqrt(np.mean(all_actions**2))),
        "action_total_variation": float(sum(record_variations)),
        "minimum_record_total_variation": float(min(record_variations)),
        "maximum_action_row_dispersion": float(max(record_dispersions)),
        "minimum_record_action_row_dispersion": float(min(record_dispersions)),
        "action_saturation_fraction": float(np.mean(saturation)),
        "action_bound_violation": bound_violation,
        "action_slew_violation": slew_violation,
        "actuator_mapping_pass": mapping_pass,
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


def _summary_is_valid(summary: Mapping[str, Any]) -> bool:
    try:
        numeric = np.asarray(
            [float(summary[key]) for key in _SUMMARY_NUMERIC_KEYS], dtype=float
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        summary.get("valid") is True
        and summary.get("record_count") == 6
        and summary.get("actuator_mapping_pass") is True
        and summary.get("action_bound_violation") is False
        and summary.get("action_slew_violation") is False
        and np.all(np.isfinite(numeric))
        and np.all(numeric >= 0.0)
        and 0.0 <= float(summary["action_saturation_fraction"]) <= 1.0
    )


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


def _aggregate(
    rows: Sequence[Mapping[str, Any]], key: str
) -> float:
    return float(sum(float(row[key]) for row in rows))


def _leave_one_out_range(
    baseline: Mapping[str, Mapping[str, Any]],
    selected: Mapping[str, Mapping[str, Any]],
    *,
    key: str,
) -> list[float]:
    values = []
    profile_ids = sorted(baseline)
    for omitted in profile_ids:
        baseline_value = sum(
            float(row[key])
            for profile_id, row in baseline.items()
            if profile_id != omitted
        )
        selected_value = sum(
            float(row[key])
            for profile_id, row in selected.items()
            if profile_id != omitted
        )
        values.append((baseline_value - selected_value) / baseline_value)
    return [float(min(values)), float(max(values))]


def classify_bank(
    summaries: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify one complete profile-by-arm bank without learning outputs."""

    spec = build_contract() if contract is None else contract
    profiles = {str(row["profile_id"]): row for row in spec["profiles"]}
    expected_arms = [str(value) for value in spec["arm_ids"]]
    expected_keys = {
        (profile_id, arm_id)
        for profile_id in profiles
        for arm_id in expected_arms
    }
    by_key: dict[tuple[str, str], Mapping[str, Any]] = {}
    duplicates = False
    split_mismatch = False
    for summary in summaries:
        profile_id = str(summary.get("profile_id", ""))
        arm_id = str(summary.get("arm_id", ""))
        key = (profile_id, arm_id)
        if key in by_key:
            duplicates = True
        by_key[key] = summary
        if profile_id in profiles and str(summary.get("split", "")) != str(
            profiles[profile_id]["split"]
        ):
            split_mismatch = True
    complete_bank = not duplicates and set(by_key) == expected_keys
    valid_rows = complete_bank and all(_summary_is_valid(row) for row in by_key.values())
    checks = {
        "complete_bank": bool(complete_bank),
        "all_rows_valid": bool(valid_rows),
        "split_identity": not split_mismatch,
        "reward_unused": spec.get("reward_used_for_gate") is False,
        "training_forbidden": spec.get("training_authorized") is False,
    }
    invalid = {
        "schema_version": 1,
        "round": str(spec["round"]),
        "manuscript_line": str(spec["manuscript_line"]),
        "classification": "ANALYSIS-INVALID",
        "checks": checks,
        "selected_deterministic_arm": None,
        "training_authorized": False,
        "claim_scope": "frozen finite heterogeneous bank only",
    }
    if not all(checks.values()):
        return invalid

    thresholds = spec["thresholds"]
    maximum_common_harm = float(thresholds["maximum_common_harm"])
    maximum_saturation = float(
        thresholds["maximum_action_saturation_fraction"]
    )
    development_ids = [
        profile_id
        for profile_id, profile in profiles.items()
        if profile["split"] == "development"
    ]
    evaluation_ids = [
        profile_id
        for profile_id, profile in profiles.items()
        if profile["split"] == "evaluation"
    ]
    zero_development = [by_key[(profile_id, "zero")] for profile_id in development_ids]
    zero_off = _aggregate(zero_development, "off_diagonal_response_energy")
    zero_differential = _aggregate(
        zero_development, "disturbance_differential_energy"
    )
    if min(zero_off, zero_differential) <= 0.0:
        checks["positive_development_reference"] = False
        return invalid
    checks["positive_development_reference"] = True

    candidate_details: dict[str, dict[str, Any]] = {}
    ranked: list[tuple[float, float, float, str]] = []
    for arm_id in spec["candidate_arm_ids"]:
        arm = str(arm_id)
        arm_rows = [by_key[(profile_id, arm)] for profile_id in development_ids]
        per_profile_common = {
            profile_id: _common_guard(
                by_key[(profile_id, arm)],
                by_key[(profile_id, "zero")],
                maximum_harm=maximum_common_harm,
            )
            for profile_id in development_ids
        }
        guard_checks = {
            "valid": all(_summary_is_valid(row) for row in arm_rows),
            "common_no_harm": all(
                all(values.values()) for values in per_profile_common.values()
            ),
            "saturation_budget": all(
                float(row["action_saturation_fraction"]) <= maximum_saturation
                for row in arm_rows
            ),
        }
        off_value = _aggregate(arm_rows, "off_diagonal_response_energy")
        differential_value = _aggregate(
            arm_rows, "disturbance_differential_energy"
        )
        off_ratio = off_value / zero_off
        differential_ratio = differential_value / zero_differential
        worst_ratio = max(off_ratio, differential_ratio)
        ratio_sum = off_ratio + differential_ratio
        action_rms = _aggregate(arm_rows, "action_rms")
        passed = all(guard_checks.values())
        candidate_details[arm] = {
            "passed": passed,
            "checks": guard_checks,
            "per_profile_common_guards": per_profile_common,
            "off_diagonal_ratio_to_zero": off_ratio,
            "differential_ratio_to_zero": differential_ratio,
            "selection_worst_ratio": worst_ratio,
            "selection_ratio_sum": ratio_sum,
            "aggregate_action_rms": action_rms,
        }
        if passed:
            ranked.append((worst_ratio, ratio_sum, action_rms, arm))
    ranked.sort()
    if not ranked:
        checks["eligible_deterministic_candidate"] = False
        return invalid
    checks["eligible_deterministic_candidate"] = True
    selected_arm = ranked[0][3]
    development_gate = {
        "selected_arm": selected_arm,
        "selection_uses_evaluation": False,
        "zero_off_diagonal_energy": zero_off,
        "zero_differential_energy": zero_differential,
        "candidates": candidate_details,
    }

    maximum_stress_harm = float(thresholds["maximum_action_stress_harm"])
    baseline_by_profile = {
        profile_id: by_key[(profile_id, selected_arm)]
        for profile_id in evaluation_ids
    }
    selected_by_profile: dict[str, Mapping[str, Any]] = {}
    selected_rows: list[dict[str, Any]] = []
    oracle_all_guards = True
    for profile_id in evaluation_ids:
        baseline = baseline_by_profile[profile_id]
        profile_ranked: list[tuple[float, float, float, str, Mapping[str, Any], dict[str, Any]]] = []
        baseline_off = float(baseline["off_diagonal_response_energy"])
        baseline_differential = float(baseline["disturbance_differential_energy"])
        if min(baseline_off, baseline_differential) <= 0.0:
            checks["positive_evaluation_reference"] = False
            return invalid
        for arm_id in spec["candidate_arm_ids"]:
            arm = str(arm_id)
            row = by_key[(profile_id, arm)]
            common_checks = _common_guard(
                row, baseline, maximum_harm=maximum_common_harm
            )
            stress_checks = {
                "action_rms_no_harm": _not_harmed(
                    float(row["action_rms"]),
                    float(baseline["action_rms"]),
                    maximum_stress_harm,
                ),
                "action_variation_no_harm": _not_harmed(
                    float(row["action_total_variation"]),
                    float(baseline["action_total_variation"]),
                    maximum_stress_harm,
                ),
            }
            guard_checks = {
                "valid": _summary_is_valid(row),
                **common_checks,
                **stress_checks,
                "saturation_budget": float(row["action_saturation_fraction"])
                <= maximum_saturation,
            }
            if not all(guard_checks.values()):
                continue
            off_ratio = float(row["off_diagonal_response_energy"]) / baseline_off
            differential_ratio = (
                float(row["disturbance_differential_energy"])
                / baseline_differential
            )
            profile_ranked.append(
                (
                    max(off_ratio, differential_ratio),
                    off_ratio + differential_ratio,
                    float(row["action_rms"]),
                    arm,
                    row,
                    guard_checks,
                )
            )
        profile_ranked.sort(key=lambda value: value[:4])
        if not profile_ranked:
            checks["eligible_oracle_candidate_each_profile"] = False
            return invalid
        _, _, _, arm, row, guard_checks = profile_ranked[0]
        selected_by_profile[profile_id] = row
        oracle_all_guards = oracle_all_guards and all(guard_checks.values())
        selected_rows.append(
            {
                "profile_id": profile_id,
                "arm_id": arm,
                "off_diagonal_response_energy": float(
                    row["off_diagonal_response_energy"]
                ),
                "disturbance_differential_energy": float(
                    row["disturbance_differential_energy"]
                ),
                "common_frequency_iae_hz_s": float(
                    row["common_frequency_iae_hz_s"]
                ),
                "worst_unit_peak_hz": float(row["worst_unit_peak_hz"]),
                "worst_rocof_hz_s": float(row["worst_rocof_hz_s"]),
                "action_rms": float(row["action_rms"]),
                "action_total_variation": float(row["action_total_variation"]),
                "minimum_record_total_variation": float(
                    row["minimum_record_total_variation"]
                ),
                "minimum_record_action_row_dispersion": float(
                    row["minimum_record_action_row_dispersion"]
                ),
                "checks": guard_checks,
            }
        )
    checks["positive_evaluation_reference"] = True
    checks["eligible_oracle_candidate_each_profile"] = True

    baseline_off = _aggregate(
        list(baseline_by_profile.values()), "off_diagonal_response_energy"
    )
    baseline_differential = _aggregate(
        list(baseline_by_profile.values()), "disturbance_differential_energy"
    )
    oracle_off = _aggregate(
        list(selected_by_profile.values()), "off_diagonal_response_energy"
    )
    oracle_differential = _aggregate(
        list(selected_by_profile.values()), "disturbance_differential_energy"
    )
    off_improvement = (baseline_off - oracle_off) / baseline_off
    differential_improvement = (
        baseline_differential - oracle_differential
    ) / baseline_differential
    minimum_improvement = float(thresholds["minimum_joint_improvement"])
    off_pass = off_improvement >= minimum_improvement - 1.0e-15
    differential_pass = (
        differential_improvement >= minimum_improvement - 1.0e-15
    )
    nonconstant_pass = all(
        float(row["minimum_record_total_variation"])
        > float(thresholds["nonconstant_action_variation_floor"])
        for row in selected_by_profile.values()
    )
    independent_action_pass = all(
        float(row["minimum_record_action_row_dispersion"])
        > float(thresholds["independent_action_dispersion_floor"])
        for row in selected_by_profile.values()
    )
    oracle_gate = {
        "passed": bool(
            off_pass
            and differential_pass
            and oracle_all_guards
            and nonconstant_pass
            and independent_action_pass
        ),
        "role": str(spec["oracle_role"]),
        "selected_profiles": selected_rows,
        "baseline_off_diagonal_energy": baseline_off,
        "oracle_off_diagonal_energy": oracle_off,
        "off_diagonal_improvement": off_improvement,
        "off_diagonal_pass": bool(off_pass),
        "baseline_differential_energy": baseline_differential,
        "oracle_differential_energy": oracle_differential,
        "differential_improvement": differential_improvement,
        "differential_pass": bool(differential_pass),
        "minimum_joint_improvement": minimum_improvement,
        "all_no_harm_and_stress_guards": bool(oracle_all_guards),
        "nonconstant_action_pass": bool(nonconstant_pass),
        "independent_per_vsg_action_pass": bool(independent_action_pass),
        "leave_one_profile_out_off_diagonal_range": _leave_one_out_range(
            baseline_by_profile,
            selected_by_profile,
            key="off_diagonal_response_energy",
        ),
        "leave_one_profile_out_differential_range": _leave_one_out_range(
            baseline_by_profile,
            selected_by_profile,
            key="disturbance_differential_energy",
        ),
    }
    return {
        "schema_version": 1,
        "round": str(spec["round"]),
        "manuscript_line": str(spec["manuscript_line"]),
        "classification": (
            "HEADROOM-PASS" if oracle_gate["passed"] else "STOP-NO-JOINT-HEADROOM"
        ),
        "checks": checks,
        "selected_deterministic_arm": selected_arm,
        "development_gate": development_gate,
        "oracle_gate": oracle_gate,
        "oracle_deployable": False,
        "reward_used_for_gate": False,
        "training_authorized": False,
        "claim_scope": "frozen finite heterogeneous bank only",
    }


__all__ = ["build_contract", "classify_bank", "summarise_profile"]
