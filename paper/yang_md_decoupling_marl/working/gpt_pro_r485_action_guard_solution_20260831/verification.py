#!/usr/bin/env python3
"""Deterministic verification for the R485 action-guard construct audit.

This script reads the original GPT Pro input ZIP in place. It does not modify or
repackage any source data. It verifies package hashes, enumerates the frozen
832 guard decisions, recomputes normalized action RMS/TV from the eight raw
candidate/comparator profiles included in the package, checks the registered
action decoder on every included raw step, and evaluates the two mathematical
counterexamples used in SOLUTION.md.

Standard-library only; Python 3.10+.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import sys
import zipfile
from pathlib import Path
from typing import Any, Iterable

M = 1.10
ACTION_LOW = -1.0
ACTION_HIGH = 1.0
SLEW_LIMIT = 0.25
M_LOWER = 20.0
D_LOWER = 10.0
NEGATIVE_GAIN = 200.0
POSITIVE_GAIN = 600.0

FORMAL = (
    "results/research_loop/r485_60hz_source_factorial/"
    "r485-formal-20260829-a/formal_analysis.json"
)
AUDIT = "tmp/r485_postrun_data_audit.json"
CONFIG = "memory/rounds/R485/config.json"
SOURCE_METRICS = "src/andes_rl_kundur/evaluation/md_decoupling_headroom.py"
SOURCE_GUARD = "src/andes_rl_kundur/evaluation/r484_tail_guard.py"
RAW_PREFIX = (
    "results/research_loop/r485_60hz_source_factorial/"
    "r485-formal-20260829-a/eval/same"
)
CANDIDATE_ARM = "an_cp_r0/seed501"
REFERENCE_ARM = "local_neighbour_md_km2_kd2/deterministic"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(zf: zipfile.ZipFile, name: str) -> Any:
    with zf.open(name) as handle:
        return json.load(handle)


def parse_sha256sums(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        result[name] = digest
    return result


def decoder(value: float) -> float:
    return value * (POSITIVE_GAIN if value >= 0.0 else NEGATIVE_GAIN)


def flatten_action(step: dict[str, Any]) -> list[float]:
    action = step["action_norm"]
    assert isinstance(action, list) and len(action) == 4
    flat: list[float] = []
    for row in action:
        assert isinstance(row, list) and len(row) == 2
        flat.extend(float(v) for v in row)
    return flat


def raw_profile_metrics(payload: dict[str, Any]) -> dict[str, float | int]:
    records = payload["records"]
    assert isinstance(records, list) and len(records) == 6
    sum_sq = 0.0
    count = 0
    total_variation = 0.0
    max_slew = 0.0
    mapping_failures = 0
    bound_failures = 0
    step_count = 0

    for record in records:
        identity = record["identity"]
        baseline_m = [float(v) for v in identity["baseline_m0"]]
        baseline_d = [float(v) for v in identity["baseline_d0"]]
        steps = record["steps"]
        assert isinstance(steps, list) and len(steps) == 150
        previous = [0.0] * 8
        for expected_index, step in enumerate(steps):
            assert int(step["step_index"]) == expected_index
            current = flatten_action(step)
            delta_sum = 0.0
            for value, old in zip(current, previous):
                if value < ACTION_LOW - 1e-12 or value > ACTION_HIGH + 1e-12:
                    bound_failures += 1
                d = abs(value - old)
                max_slew = max(max_slew, d)
                delta_sum += d
                sum_sq += value * value
                count += 1
            total_variation += delta_sum / 8.0
            previous = current

            expected_dm = [decoder(current[2 * i]) for i in range(4)]
            expected_dd = [decoder(current[2 * i + 1]) for i in range(4)]
            actual_dm = [float(v) for v in step["delta_M"]]
            actual_dd = [float(v) for v in step["delta_D"]]
            actual_m = [float(v) for v in step["M_es"]]
            actual_d = [float(v) for v in step["D_es"]]
            for i in range(4):
                expected_m = max(baseline_m[i] + expected_dm[i], M_LOWER)
                expected_d = max(baseline_d[i] + expected_dd[i], D_LOWER)
                checks = (
                    abs(actual_dm[i] - expected_dm[i]),
                    abs(actual_dd[i] - expected_dd[i]),
                    abs(actual_m[i] - expected_m),
                    abs(actual_d[i] - expected_d),
                )
                if max(checks) > 3.0517578125e-05 + 1e-12:
                    mapping_failures += 1
            step_count += 1

    assert count == 6 * 150 * 8
    assert step_count == 6 * 150
    return {
        "action_rms": math.sqrt(sum_sq / count),
        "action_total_variation": total_variation,
        "max_observed_slew": max_slew,
        "mapping_failures": mapping_failures,
        "bound_failures": bound_failures,
        "records": len(records),
        "steps": step_count,
    }


def vector_metrics(records: list[list[list[float]]]) -> tuple[float, float]:
    """R/V for generic records[record][time][channel]."""
    n = len(records)
    assert n > 0
    t = len(records[0])
    c = len(records[0][0])
    assert t > 0 and c > 0
    sum_sq = 0.0
    tv = 0.0
    count = 0
    for record in records:
        assert len(record) == t
        prev = [0.0] * c
        for row in record:
            assert len(row) == c
            tv += sum(abs(float(x) - prev[j]) for j, x in enumerate(row)) / c
            for x in row:
                sum_sq += float(x) ** 2
                count += 1
            prev = [float(x) for x in row]
    return math.sqrt(sum_sq / count), tv


def verify_scaling_identities() -> dict[str, float]:
    x = [[[0.2, -0.1], [0.3, 0.1], [0.0, 0.2]]]
    r, v = vector_metrics(x)

    duplicated_records = x + json.loads(json.dumps(x))
    rr, vr = vector_metrics(duplicated_records)
    assert math.isclose(rr, r, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(vr, 2.0 * v, rel_tol=0.0, abs_tol=1e-15)

    duplicated_channels = [
        [[*row, *row] for row in record]
        for record in x
    ]
    rc, vc = vector_metrics(duplicated_channels)
    assert math.isclose(rc, r, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(vc, v, rel_tol=0.0, abs_tol=1e-15)

    scale = -3.0
    scaled = [
        [[scale * value for value in row] for row in record]
        for record in x
    ]
    rs, vs = vector_metrics(scaled)
    assert math.isclose(rs, abs(scale) * r, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(vs, abs(scale) * v, rel_tol=0.0, abs_tol=1e-15)

    pulse_short = [[[1.0], [0.0], *([[0.0]] * 8)]]
    pulse_long = [[[1.0], [0.0], *([[0.0]] * 38)]]
    r_short, v_short = vector_metrics(pulse_short)
    r_long, v_long = vector_metrics(pulse_long)
    assert math.isclose(r_long / r_short, 0.5, rel_tol=0.0, abs_tol=1e-15)
    assert math.isclose(v_long, v_short, rel_tol=0.0, abs_tol=1e-15)

    jitter_10 = [[[0.01 * ((-1.0) ** k)] for k in range(10)]]
    jitter_20 = [[[0.01 * ((-1.0) ** k)] for k in range(20)]]
    r10, v10 = vector_metrics(jitter_10)
    r20, v20 = vector_metrics(jitter_20)
    assert math.isclose(r10, r20, rel_tol=0.0, abs_tol=1e-15)
    assert v20 > 2.0 * v10

    return {
        "base_rms": r,
        "base_tv": v,
        "record_duplication_tv_factor": vr / v,
        "channel_duplication_tv_factor": vc / v,
        "common_scale_rms_factor": rs / r,
        "common_scale_tv_factor": vs / v,
        "fourfold_horizon_single_pulse_rms_factor": r_long / r_short,
        "fourfold_horizon_single_pulse_tv_factor": v_long / v_short,
        "jitter_double_sample_count_rms_factor": r20 / r10,
        "jitter_double_sample_count_tv_factor": v20 / v10,
    }


def verify_counterexamples() -> dict[str, Any]:
    # Counterexample A: benign under a deadband but rejected by both ratios.
    epsilon = 0.1
    deadband = 0.25
    a1 = [[[2.0 * epsilon]]]
    b1 = [[[epsilon]]]
    ra1, va1 = vector_metrics(a1)
    rb1, vb1 = vector_metrics(b1)
    deadband_map = lambda x: 0.0 if abs(x) <= deadband else x
    harm_a1 = deadband_map(2.0 * epsilon) ** 2
    harm_b1 = deadband_map(epsilon) ** 2
    assert ra1 > M * rb1 and va1 > M * vb1
    assert harm_a1 == harm_b1 == 0.0

    # Counterexample B: passes normalized metrics, but the registered asymmetric
    # decoder gives a 9x quadratic physical-command stress ratio.
    a2 = [[[1.0]]]
    b2 = [[[-1.0]]]
    ra2, va2 = vector_metrics(a2)
    rb2, vb2 = vector_metrics(b2)
    physical_a2 = decoder(1.0)
    physical_b2 = decoder(-1.0)
    harm_a2 = physical_a2**2
    harm_b2 = physical_b2**2
    safety_limit = 100_000.0
    assert ra2 <= M * rb2 and va2 <= M * vb2
    assert harm_b2 < safety_limit < harm_a2
    assert math.isclose(harm_a2 / harm_b2, 9.0)

    return {
        "benign_but_rejected": {
            "normalized_rms_ratio": ra1 / rb1,
            "normalized_tv_ratio": va1 / vb1,
            "physical_harm_candidate": harm_a1,
            "physical_harm_reference": harm_b1,
        },
        "harmful_but_accepted": {
            "normalized_rms_ratio": ra2 / rb2,
            "normalized_tv_ratio": va2 / vb2,
            "decoded_candidate": physical_a2,
            "decoded_reference": physical_b2,
            "quadratic_stress_ratio": harm_a2 / harm_b2,
            "safety_limit": safety_limit,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-zip", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    with zipfile.ZipFile(args.input_zip) as zf:
        names = set(zf.namelist())
        manifest = load_json(zf, "manifest.json")
        sums = parse_sha256sums(zf.read("SHA256SUMS").decode("utf-8"))
        manifest_files = dict(manifest["files"])
        assert manifest_files == sums
        assert set(sums).issubset(names)

        hash_failures: list[str] = []
        for name, expected in sums.items():
            actual = sha256(zf.read(name))
            if actual != expected:
                hash_failures.append(name)
        assert not hash_failures

        sidecar_failures: list[str] = []
        for name in sorted(n for n in names if n.endswith(".sha256")):
            target = name[: -len(".sha256")]
            declared = zf.read(name).decode("utf-8").strip().split()[0]
            if target not in names or declared != sha256(zf.read(target)):
                sidecar_failures.append(name)
        assert not sidecar_failures

        assert len(manifest["problems"]) == 1
        problem = manifest["problems"][0]
        assert problem["id"] == "yang-r485-action-guard-construct-validity"
        assert problem["status"] == "open"
        assert problem["missing"] == []

        config = load_json(zf, CONFIG)
        assert config["evaluation"]["steps"] == 150
        assert math.isclose(config["evaluation"]["dt_seconds"], 0.2)

        metric_source = zf.read(SOURCE_METRICS).decode("utf-8")
        guard_source = zf.read(SOURCE_GUARD).decode("utf-8")
        for snippet in (
            "np.sqrt(np.mean(all_actions**2))",
            "np.sum(np.mean(np.abs(differences), axis=(1, 2)))",
            '"action_bounds": [-1.0, 1.0]',
            '"action_slew_limit": 0.25',
            '"delta_m_negative": -200.0',
            '"delta_m_positive": 600.0',
        ):
            assert snippet in metric_source
        for snippet in (
            '"maximum_action_stress_harm": 0.10',
            '"action_rms_no_harm"',
            '"action_variation_no_harm"',
        ):
            assert snippet in guard_source

        formal = load_json(zf, FORMAL)
        audit = load_json(zf, AUDIT)
        assert formal["status"] == "VALID-MIXED"
        assert formal["learner_qualification"]["endpoint_qualified_count"] == 121
        assert formal["learner_qualification"]["complete_contract_passing_count"] == 0

        threshold = formal["threshold_sensitivity"]
        primary = threshold["primary"]
        blocks = primary["per_profile_blocks"]
        decisions = primary["policy_decisions"]
        break_even = threshold["break_even"]
        assert len(blocks) == 832
        assert len(decisions) == 208
        assert len(break_even) == 208
        rms_failures = sum(not row["guard"]["action_rms_no_harm"] for row in blocks)
        tv_failures = sum(not row["guard"]["action_variation_no_harm"] for row in blocks)
        assert rms_failures == 832 and tv_failures == 832
        endpoint_qualified = sum(
            all(row["aggregate_joint_endpoint_target"].values()) for row in decisions
        )
        complete_passes = sum(row["passed_complete_guard"] for row in decisions)
        assert endpoint_qualified == 121 and complete_passes == 0
        assert len(threshold["grid"]) == 16
        assert all(row["passing_count"] == 0 for row in threshold["grid"])

        action_break_even = [float(row["action_only_break_even"]) for row in break_even]
        complete_break_even = [
            float(row["complete_contract_break_even"])
            for row in break_even
            if row["complete_contract_break_even"] is not None
        ]
        assert len(complete_break_even) == 5

        continuous = audit["continuous_ratios"]["all_policy_profile_blocks"]
        rms_ratios = continuous["action_rms"]
        tv_ratios = continuous["action_total_variation"]
        assert rms_ratios["n"] == tv_ratios["n"] == 832
        assert math.isclose(min(action_break_even), audit["why_complete_guard_failed"]["action_only_break_even"]["min"])
        assert math.isclose(max(action_break_even), audit["why_complete_guard_failed"]["action_only_break_even"]["max"])
        assert audit["why_complete_guard_failed"]["policies_all_non_action_guards_and_endpoints_pass"] == 5

        raw_rows: list[dict[str, Any]] = []
        for letter in "abcd":
            profile = f"canary_eval_{letter}"
            candidate_name = f"{RAW_PREFIX}/{CANDIDATE_ARM}/{profile}.json"
            reference_name = f"{RAW_PREFIX}/{REFERENCE_ARM}/{profile}.json"
            candidate = raw_profile_metrics(load_json(zf, candidate_name))
            reference = raw_profile_metrics(load_json(zf, reference_name))
            assert candidate["mapping_failures"] == reference["mapping_failures"] == 0
            assert candidate["bound_failures"] == reference["bound_failures"] == 0
            assert float(candidate["max_observed_slew"]) <= SLEW_LIMIT + 1e-12
            assert float(reference["max_observed_slew"]) <= SLEW_LIMIT + 1e-12
            raw_rows.append(
                {
                    "profile": profile,
                    "candidate_action_rms": candidate["action_rms"],
                    "reference_action_rms": reference["action_rms"],
                    "action_rms_ratio": float(candidate["action_rms"]) / float(reference["action_rms"]),
                    "candidate_action_total_variation": candidate["action_total_variation"],
                    "reference_action_total_variation": reference["action_total_variation"],
                    "action_tv_ratio": float(candidate["action_total_variation"]) / float(reference["action_total_variation"]),
                    "candidate_max_observed_slew": candidate["max_observed_slew"],
                    "reference_max_observed_slew": reference["max_observed_slew"],
                }
            )

    scaling = verify_scaling_identities()
    counterexamples = verify_counterexamples()

    q_r_min = float(rms_ratios["min"])
    q_v_min = float(tv_ratios["min"])
    derived = {
        "schema_version": 1,
        "verification_status": "PASS",
        "runtime": {
            "python": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "input": {
            "zip_name": args.input_zip.name,
            "zip_sha256": sha256(args.input_zip.read_bytes()),
            "member_count": len(names),
            "hashed_manifest_files": len(sums),
            "sidecars_checked": len([n for n in names if n.endswith('.sha256')]),
            "problem_count": 1,
            "problem_id": problem["id"],
        },
        "frozen_result": {
            "status": formal["status"],
            "endpoint_qualified": endpoint_qualified,
            "complete_passes": complete_passes,
            "profile_blocks": len(blocks),
            "action_rms_failures": rms_failures,
            "action_tv_failures": tv_failures,
            "threshold_grid_cells": len(threshold["grid"]),
            "threshold_grid_complete_passes": sum(row["passing_count"] for row in threshold["grid"]),
            "non_action_and_endpoint_pass_policies": len(complete_break_even),
            "complete_contract_break_even_values": sorted(complete_break_even),
        },
        "all_832_ratio_distribution": {
            "action_rms": rms_ratios,
            "action_total_variation": tv_ratios,
            "minimum_rms_ratio_over_registered_cap": q_r_min / M,
            "minimum_tv_ratio_over_registered_cap": q_v_min / M,
            "minimum_rms_candidate_reduction_to_reach_cap": 1.0 - M / q_r_min,
            "minimum_tv_candidate_reduction_to_reach_cap": 1.0 - M / q_v_min,
        },
        "raw_recomputation": raw_rows,
        "registered_tv_upper_bound": {
            "records": 6,
            "steps_per_record": 150,
            "slew_limit_per_step": SLEW_LIMIT,
            "maximum_possible_tv": 6 * 150 * SLEW_LIMIT,
        },
        "scaling_identity_checks": scaling,
        "counterexamples": counterexamples,
    }

    if args.json_out is not None:
        args.json_out.write_text(
            json.dumps(derived, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print("R485 ACTION-GUARD VERIFICATION: PASS")
    print(f"runtime: Python {platform.python_version()} ({platform.python_implementation()})")
    print(f"input zip sha256: {derived['input']['zip_sha256']}")
    print(f"package hashes: {len(sums)}/{len(sums)}; sidecars: {derived['input']['sidecars_checked']}")
    print(f"selected problem roster: 1/1 ({problem['id']})")
    print(
        "frozen result: endpoint-qualified=121/208, complete=0/208, "
        "action-RMS failures=832/832, action-TV failures=832/832"
    )
    print(
        "all-block action ratios (min/median/max): "
        f"RMS={rms_ratios['min']:.6f}/{rms_ratios['median']:.6f}/{rms_ratios['max']:.6f}; "
        f"TV={tv_ratios['min']:.6f}/{tv_ratios['median']:.6f}/{tv_ratios['max']:.6f}"
    )
    print(
        "distance from 1.10 cap at the nearest block: "
        f"RMS needs {100*(1-M/q_r_min):.3f}% candidate reduction; "
        f"TV needs {100*(1-M/q_v_min):.3f}% candidate reduction"
    )
    print("raw recomputation for included an_cp_r0/seed501 vs deterministic comparator:")
    for row in raw_rows:
        print(
            f"  {row['profile']}: "
            f"R={row['candidate_action_rms']:.9f}/{row['reference_action_rms']:.9f} "
            f"(x{row['action_rms_ratio']:.6f}); "
            f"V={row['candidate_action_total_variation']:.9f}/{row['reference_action_total_variation']:.9f} "
            f"(x{row['action_tv_ratio']:.6f})"
        )
    print(
        "counterexample A: physically benign under deadband, but normalized "
        "RMS/TV ratios are both 2.0 and fail"
    )
    print(
        "counterexample B: normalized RMS/TV ratios are both 1.0 and pass, "
        "while the registered +600/-200 decoder gives a 9.0x quadratic-stress ratio"
    )
    if args.json_out is not None:
        print(f"derived JSON: {args.json_out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"R485 ACTION-GUARD VERIFICATION: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
