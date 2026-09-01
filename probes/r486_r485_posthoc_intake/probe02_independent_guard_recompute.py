"""PROTOTYPE: independently recompute R485 profile metrics and guards.

This file intentionally imports no project analysis function.  It reads the
sealed parameter card and step records, recomputes the registered estimators,
and compares every exposed guard/ratio/decision with formal_analysis.json.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
ROUND_DIR = ROOT / "memory" / "rounds" / "R485"
ATTEMPT = ROOT / "results" / "research_loop" / "r485_60hz_source_factorial" / "r485-formal-20260829-a"
DIRECT = "local_neighbour_md_km2_kd2"
MINIMUM_JOINT_IMPROVEMENT = 0.05


def close(a: float, b: float) -> bool:
    return math.isclose(float(a), float(b), rel_tol=1.0e-12, abs_tol=1.0e-9)


def arrays(record: dict[str, Any], contract: dict[str, Any]) -> dict[str, np.ndarray]:
    steps = record["steps"]
    action = np.asarray([row["action_norm"] for row in steps], dtype=float)
    frequency = np.asarray([row["freq_hz_physical"] for row in steps], dtype=float)
    delta_m = np.asarray([row["delta_M"] for row in steps], dtype=float)
    delta_d = np.asarray([row["delta_D"] for row in steps], dtype=float)
    actual_m = np.asarray([row["M_es"] for row in steps], dtype=float)
    actual_d = np.asarray([row["D_es"] for row in steps], dtype=float)
    if action.shape != (150, 4, 2) or frequency.shape != (150, 4):
        raise ValueError(f"shape mismatch in {record['scenario_id']}")
    identity = record["identity"]
    base_m = np.asarray(identity["baseline_m0"], dtype=float)
    base_d = np.asarray(identity["baseline_d0"], dtype=float)
    decoder = contract["decoder"]
    expected_delta_m = np.where(
        action[:, :, 0] >= 0.0,
        action[:, :, 0] * float(decoder["delta_m_positive"]),
        action[:, :, 0] * -float(decoder["delta_m_negative"]),
    )
    expected_delta_d = np.where(
        action[:, :, 1] >= 0.0,
        action[:, :, 1] * float(decoder["delta_d_positive"]),
        action[:, :, 1] * -float(decoder["delta_d_negative"]),
    )
    expected_m = np.maximum(base_m[None, :] + expected_delta_m, float(decoder["m_lower_clamp"]))
    expected_d = np.maximum(base_d[None, :] + expected_delta_d, float(decoder["d_lower_clamp"]))
    atol = float(decoder["mapping_atol"])
    mapping = np.asarray(
        [
            np.allclose(delta_m, expected_delta_m, rtol=0.0, atol=atol),
            np.allclose(delta_d, expected_delta_d, rtol=0.0, atol=atol),
            np.allclose(actual_m, expected_m, rtol=0.0, atol=atol),
            np.allclose(actual_d, expected_d, rtol=0.0, atol=atol),
        ]
    )
    return {
        "action": action,
        "frequency": frequency,
        "initial": np.asarray(record["initial_freq_hz_physical"], dtype=float),
        "mapping": mapping,
    }


def summarise(records: list[dict[str, Any]], contract: dict[str, Any]) -> dict[str, Any]:
    if len(records) != 6:
        raise ValueError("profile block must contain six records")
    profile_id = records[0]["profile_id"]
    profile = next(row for row in contract["profiles"] if row["profile_id"] == profile_id)
    registered = {row["scenario_id"]: row for row in profile["scenarios"]}
    if {row["scenario_id"] for row in records} != set(registered):
        raise ValueError(f"scenario roster mismatch: {profile_id}")
    by_scenario = {row["scenario_id"]: row for row in records}
    data = {key: arrays(row, contract) for key, row in by_scenario.items()}
    dt = float(contract["dt_seconds"])
    nominal = float(contract["physical_nominal_frequency_hz"])
    transform = np.asarray(contract["differential_transform"], dtype=float)
    responses: dict[str, dict[str, Any]] = {}
    for kind in ("common", "differential", "localized"):
        positive = data[f"{profile_id}_{kind}_positive"]["frequency"] - nominal
        negative = data[f"{profile_id}_{kind}_negative"]["frequency"] - nominal
        odd = 0.5 * (positive - negative)
        responses[kind] = {
            "common": np.mean(odd, axis=1),
            "differential": odd @ transform.T,
            "magnitude": float(registered[f"{profile_id}_{kind}_positive"]["magnitude"]),
        }
    off = (
        float(np.sum(np.mean(responses["common"]["differential"] ** 2, axis=1)))
        * dt
        / responses["common"]["magnitude"] ** 2
        + float(np.sum(responses["differential"]["common"] ** 2))
        * dt
        / responses["differential"]["magnitude"] ** 2
    )
    differential = sum(
        float(np.sum(np.mean(responses[kind]["differential"] ** 2, axis=1)))
        * dt
        / responses[kind]["magnitude"] ** 2
        for kind in ("common", "differential", "localized")
    )
    frequency_blocks = [value["frequency"] for value in data.values()]
    common_iae = sum(float(np.sum(np.abs(np.mean(value - nominal, axis=1))) * dt) for value in frequency_blocks)
    worst_peak = max(float(np.max(np.abs(value - nominal))) for value in frequency_blocks)
    worst_rocof = max(
        float(np.max(np.abs(np.diff(np.concatenate([value["initial"][None, :], value["frequency"]], axis=0), axis=0) / dt)))
        for value in data.values()
    )
    action_blocks = [value["action"] for value in data.values()]
    all_actions = np.stack(action_blocks)
    zero_differences = [np.diff(np.concatenate([np.zeros((1, 4, 2)), value], axis=0), axis=0) for value in action_blocks]
    record_tv = [float(np.sum(np.mean(np.abs(value), axis=(1, 2)))) for value in zero_differences]
    no_initial_tv = [float(np.sum(np.mean(np.abs(np.diff(value, axis=0)), axis=(1, 2)))) for value in action_blocks]
    dispersions = [float(np.max(np.ptp(value, axis=1))) for value in action_blocks]
    lower, upper = map(float, contract["action_bounds"])
    tolerance = 1.0e-9
    saturation = np.logical_or(all_actions <= lower + tolerance, all_actions >= upper - tolerance)
    mapping_pass = all(bool(np.all(value["mapping"])) for value in data.values())
    bound_violation = bool(np.any(all_actions < lower - tolerance) or np.any(all_actions > upper + tolerance))
    slew_violation = any(bool(np.any(np.abs(value) > float(contract["action_slew_limit"]) + tolerance)) for value in zero_differences)
    times_regular = all(
        np.allclose(np.diff([step["time"] for step in record["steps"]]), dt, rtol=0.0, atol=1.0e-9)
        for record in records
    )
    finite = all(np.all(np.isfinite(value)) for value in [all_actions, *frequency_blocks])
    return {
        "profile_id": profile_id,
        "arm_id": records[0]["arm_id"],
        "training_seed": records[0]["training_seed"],
        "off_diagonal_response_energy": off,
        "disturbance_differential_energy": differential,
        "common_frequency_iae_hz_s": common_iae,
        "worst_unit_peak_hz": worst_peak,
        "worst_rocof_hz_s": worst_rocof,
        "action_rms": float(np.sqrt(np.mean(all_actions**2))),
        "action_total_variation": float(sum(record_tv)),
        "action_total_variation_without_zero_to_first": float(sum(no_initial_tv)),
        "minimum_record_total_variation": float(min(record_tv)),
        "minimum_record_action_row_dispersion": float(min(dispersions)),
        "action_saturation_fraction": float(np.mean(saturation)),
        "actuator_mapping_pass": mapping_pass,
        "action_bound_violation": bound_violation,
        "action_slew_violation": slew_violation,
        "valid": bool(finite and times_regular and mapping_pass and not bound_violation and not slew_violation),
    }


def block_guard(candidate: dict[str, Any], reference: dict[str, Any], frequency_multiplier: float, action_multiplier: float, thresholds: dict[str, Any]) -> dict[str, bool]:
    return {
        "valid": candidate["valid"] is True,
        "actuator_mapping_pass": candidate["actuator_mapping_pass"] is True,
        "action_bound_violation": candidate["action_bound_violation"] is False,
        "action_slew_violation": candidate["action_slew_violation"] is False,
        "common_frequency_no_harm": candidate["common_frequency_iae_hz_s"] <= frequency_multiplier * reference["common_frequency_iae_hz_s"] + 1.0e-15,
        "worst_peak_no_harm": candidate["worst_unit_peak_hz"] <= frequency_multiplier * reference["worst_unit_peak_hz"] + 1.0e-15,
        "rocof_no_harm": candidate["worst_rocof_hz_s"] <= frequency_multiplier * reference["worst_rocof_hz_s"] + 1.0e-15,
        "action_rms_no_harm": candidate["action_rms"] <= action_multiplier * reference["action_rms"] + 1.0e-15,
        "action_variation_no_harm": candidate["action_total_variation"] <= action_multiplier * reference["action_total_variation"] + 1.0e-15,
        "saturation_budget": candidate["action_saturation_fraction"] <= float(thresholds["maximum_action_saturation_fraction"]),
        "nonconstant_action": candidate["minimum_record_total_variation"] > float(thresholds["nonconstant_action_variation_floor"]),
        "independent_per_vsg_action": candidate["minimum_record_action_row_dispersion"] > float(thresholds["independent_action_dispersion_floor"]),
    }


def run() -> dict[str, Any]:
    started = time.time()
    card = json.loads((ROUND_DIR / "resolved_parameter_card.json").read_text(encoding="utf-8"))
    config = json.loads((ROUND_DIR / "config.json").read_text(encoding="utf-8"))
    formal = json.loads((ATTEMPT / "formal_analysis.json").read_text(encoding="utf-8"))
    contract = card["evaluation_contracts"]["same"]
    thresholds = contract["thresholds"]
    profiles = tuple(row["profile_id"] for row in contract["profiles"] if row["split"] == "evaluation")
    policies = tuple((arm, seed) for arm in config["arms"] for seed in config["formal_seeds"])
    summaries: dict[tuple[str, str, int | None], dict[str, Any]] = {}
    all_same = sorted((ATTEMPT / "eval" / "same").glob("*/*/*.json"))
    files = [path for path in all_same if "deterministic" not in path.parts] + [
        path for path in all_same if "deterministic" in path.parts
    ]
    for path in files:
        records = json.loads(path.read_bytes())["records"]
        summary = summarise(records, contract)
        key = (summary["profile_id"], summary["arm_id"], summary["training_seed"])
        if key in summaries:
            raise ValueError(f"duplicate summary: {key}")
        summaries[key] = summary
    formal_blocks = {(row["profile_id"], row["arm_id"], row["training_seed"]): row for row in formal["threshold_sensitivity"]["primary"]["per_profile_blocks"]}
    formal_decisions = {(row["arm_id"], row["training_seed"]): row for row in formal["threshold_sensitivity"]["primary"]["policy_decisions"]}
    primary = card["threshold_sensitivity"]["primary"]
    metric_errors: list[str] = []
    guard_errors: list[str] = []
    decision_errors: list[str] = []
    computed_guards: dict[tuple[str, str, int], dict[str, bool]] = {}
    endpoint_qualified = 0
    complete = 0
    failure_counts: Counter[str] = Counter()
    policy_endpoint_targets: dict[tuple[str, int], dict[str, bool]] = {}
    for arm, seed in policies:
        endpoint_sums = {"off_diagonal_response_energy": 0.0, "disturbance_differential_energy": 0.0}
        reference_sums = dict.fromkeys(endpoint_sums, 0.0)
        profile_passes = 0
        for profile in profiles:
            candidate = summaries[(profile, arm, seed)]
            reference = summaries[(profile, DIRECT, None)]
            guard = block_guard(candidate, reference, float(primary["frequency"]), float(primary["action"]), thresholds)
            computed_guards[(profile, arm, seed)] = guard
            failure_counts.update(name for name, passed in guard.items() if not passed)
            profile_passes += int(all(guard.values()))
            block = formal_blocks[(profile, arm, seed)]
            if guard != block["guard"] or all(guard.values()) != block["passed"]:
                guard_errors.append(f"{profile}|{arm}|{seed}")
            for metric, formal_name in (("off_diagonal_response_energy", "off_diagonal_ratio_to_deterministic"), ("disturbance_differential_energy", "differential_ratio_to_deterministic")):
                ratio = candidate[metric] / reference[metric]
                if not close(ratio, block[formal_name]):
                    metric_errors.append(f"{profile}|{arm}|{seed}|{metric}")
                endpoint_sums[metric] += candidate[metric]
                reference_sums[metric] += reference[metric]
        ratios = {name: endpoint_sums[name] / reference_sums[name] for name in endpoint_sums}
        targets = {name: value <= 1.0 - MINIMUM_JOINT_IMPROVEMENT + 1.0e-15 for name, value in ratios.items()}
        policy_endpoint_targets[(arm, seed)] = targets
        endpoint_qualified += int(all(targets.values()))
        passed = profile_passes == 4 and all(targets.values())
        complete += int(passed)
        formal_row = formal_decisions[(arm, seed)]
        if (
            any(not close(ratios[name], formal_row["aggregate_endpoint_ratios_to_deterministic"][name]) for name in ratios)
            or targets != formal_row["aggregate_joint_endpoint_target"]
            or profile_passes != formal_row["passed_count"]
            or passed != formal_row["passed_complete_guard"]
        ):
            decision_errors.append(f"{arm}|{seed}")

    # Deterministic direct-M/D ratios and guards against zero.
    deterministic_errors: list[str] = []
    formal_direct = formal["same_bank_deterministic_gate"]["gate"]["per_profile"]
    for profile in profiles:
        direct = summaries[(profile, DIRECT, None)]
        zero = summaries[(profile, "zero", None)]
        row = formal_direct[profile]
        if not close(direct["off_diagonal_response_energy"] / zero["off_diagonal_response_energy"], row["off_diagonal_ratio_to_zero"]):
            deterministic_errors.append(f"{profile}|off")
        if not close(direct["disturbance_differential_energy"] / zero["disturbance_differential_energy"], row["differential_ratio_to_zero"]):
            deterministic_errors.append(f"{profile}|differential")
        direct_guard = block_guard(direct, direct, 1.03, 1.10, thresholds)
        structural = {name: direct_guard[name] for name in ("valid", "actuator_mapping_pass", "action_bound_violation", "action_slew_violation", "saturation_budget", "nonconstant_action", "independent_per_vsg_action")}
        for name, value in structural.items():
            if row["guard"][name] != value:
                deterministic_errors.append(f"{profile}|{name}")

    # Full frozen threshold grid.
    grid: list[dict[str, Any]] = []
    for frequency in card["threshold_sensitivity"]["frequency_multipliers"]:
        for action in card["threshold_sensitivity"]["action_multipliers"]:
            passing = 0
            for arm, seed in policies:
                four = all(
                    all(block_guard(summaries[(profile, arm, seed)], summaries[(profile, DIRECT, None)], float(frequency), float(action), thresholds).values())
                    for profile in profiles
                )
                passing += int(four and all(policy_endpoint_targets[(arm, seed)].values()))
            grid.append({"frequency_multiplier": float(frequency), "action_multiplier": float(action), "passing_count": passing})
    formal_grid = [{key: row[key] for key in ("frequency_multiplier", "action_multiplier", "passing_count")} for row in formal["threshold_sensitivity"]["grid"]]
    grid_errors = [] if grid == formal_grid else ["threshold_grid_mismatch"]

    # Break-even ratios and non-action eligibility.
    formal_break = {(row["arm_id"], row["training_seed"]): row for row in formal["threshold_sensitivity"]["break_even"]}
    break_errors: list[str] = []
    break_values: list[float] = []
    complete_break_count = 0
    for arm, seed in policies:
        ratios = []
        non_action = all(policy_endpoint_targets[(arm, seed)].values())
        for profile in profiles:
            candidate = summaries[(profile, arm, seed)]
            reference = summaries[(profile, DIRECT, None)]
            ratios.extend([candidate["action_rms"] / reference["action_rms"], candidate["action_total_variation"] / reference["action_total_variation"]])
            guard = computed_guards[(profile, arm, seed)]
            non_action &= all(value for name, value in guard.items() if name not in {"action_rms_no_harm", "action_variation_no_harm"})
        value = max(ratios)
        break_values.append(value)
        complete_break_count += int(non_action)
        row = formal_break[(arm, seed)]
        if not close(value, row["action_only_break_even"]) or bool(non_action) != row["all_non_action_guards_pass"]:
            break_errors.append(f"{arm}|{seed}")
        expected_complete = value if non_action else None
        if expected_complete is None:
            if row["complete_contract_break_even"] is not None:
                break_errors.append(f"{arm}|{seed}|complete")
        elif not close(expected_complete, row["complete_contract_break_even"]):
            break_errors.append(f"{arm}|{seed}|complete")

    first_profile = profiles[0]
    first_direct = summaries[(first_profile, DIRECT, None)]
    first_candidate = summaries[(first_profile, policies[0][0], policies[0][1])]
    negative_control = {
        "zero_to_first_tv_omission_changes_learned_tv": abs(first_candidate["action_total_variation"] - first_candidate["action_total_variation_without_zero_to_first"]) > 1.0e-9,
        "direct_zero_to_first_tv_difference": first_direct["action_total_variation"] - first_direct["action_total_variation_without_zero_to_first"],
        "learned_zero_to_first_tv_difference": first_candidate["action_total_variation"] - first_candidate["action_total_variation_without_zero_to_first"],
        "zero_arm_is_invalid_action_denominator": summaries[(first_profile, "zero", None)]["action_rms"] == 0.0,
        "candidate_direct_action_rms_ratio": first_candidate["action_rms"] / first_direct["action_rms"],
    }
    if not all(value for value in negative_control.values() if isinstance(value, bool)):
        raise AssertionError(f"negative control failed: {negative_control}")

    errors = metric_errors + guard_errors + decision_errors + deterministic_errors + grid_errors + break_errors
    result = {
        "schema_version": 1,
        "probe": "R485 pre-paper audit probe 02: independent metric and guard recomputation",
        "question": "Can formula, unit, denominator, or boundary handling manufacture 0/208?",
        "prediction_tolerance": {"absolute": 1.0e-9, "relative": 1.0e-12},
        "negative_control": negative_control,
        "observed": {
            "summaries": len(summaries),
            "learned_blocks": len(computed_guards),
            "endpoint_qualified_policies": endpoint_qualified,
            "complete_contract_policies": complete,
            "both_action_guards_failed_blocks": sum(
                int(not guard["action_rms_no_harm"] and not guard["action_variation_no_harm"])
                for guard in computed_guards.values()
            ),
            "guard_failure_counts": dict(sorted(failure_counts.items())),
            "threshold_grid_passing_counts": [row["passing_count"] for row in grid],
            "action_only_break_even": {
                "min": min(break_values),
                "median": float(np.median(break_values)),
                "max": max(break_values),
            },
            "all_non_action_guards_pass_policies": complete_break_count,
        },
        "comparison_errors": {
            "metric_ratios": metric_errors,
            "profile_guards": guard_errors,
            "policy_decisions": decision_errors,
            "deterministic_reference": deterministic_errors,
            "threshold_grid": grid_errors,
            "break_even": break_errors,
        },
        "decision": "PASS_PROCEED_TO_COMPARATOR_AND_STATISTICS" if not errors else "P0_STOP",
        "elapsed_seconds": round(time.time() - started, 3),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["decision"] != "P0_STOP" else 2


if __name__ == "__main__":
    raise SystemExit(main())
