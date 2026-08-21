"""Focused tests for the frozen Gate A canary contract and classifier.

These tests bind the pre-registered decision tree at its public seams: the
closed contract, the fresh-bank separation from R399, the development
scenario schedule, and the CANARY-PASS / CANARY-FAIL / CANARY-INVALID
branches.  No ANDES import and no learning code are exercised here.
"""

from __future__ import annotations

import json

import pytest

from andes_rl_kundur.evaluation.cd_matd3_canary import (
    TOTAL_INTERACTION_STEPS,
    TOTAL_TRAINING_EPISODES,
    build_contract,
    classify_canary,
    contract_sha256,
    evaluation_record_count,
    training_run_count,
)
from andes_rl_kundur.evaluation.md_decoupling_headroom import build_contract as build_r399_contract


def _summary(profile_id, arm_id, seed, off, diff, *, common_iae=1.0,
             peak=0.4, rocof=2.0, rms=0.2, tv=1.0, sat=0.01):
    return {
        "profile_id": profile_id,
        "split": "evaluation",
        "arm_id": arm_id,
        "training_seed": seed,
        "valid": True,
        "record_count": 6,
        "off_diagonal_response_energy": off,
        "disturbance_differential_energy": diff,
        "common_frequency_iae_hz_s": common_iae,
        "worst_unit_peak_hz": peak,
        "worst_rocof_hz_s": rocof,
        "action_rms": rms,
        "action_total_variation": tv,
        "minimum_record_total_variation": 0.01,
        "maximum_action_row_dispersion": 0.02,
        "minimum_record_action_row_dispersion": 0.01,
        "action_saturation_fraction": sat,
        "action_bound_violation": False,
        "action_slew_violation": False,
        "actuator_mapping_pass": True,
    }


def _manifest(arm_id, seed, *, steps=TOTAL_INTERACTION_STEPS,
              valid=True, missing=False, restarts=0):
    return {
        "arm_id": arm_id,
        "training_seed": seed,
        "interaction_steps": steps,
        "convergence_diagnostics_valid": valid,
        "missing": missing,
        "restart_count": restarts,
    }


def _full_bank(contract, *, full=(0.8, 0.85), no_message=(0.9, 0.92),
               scalar=(0.95, 0.98)):
    """Build one complete valid bank with the deterministic reference at 1.0."""

    evaluation_ids = [
        str(profile["profile_id"])
        for profile in contract["profiles"]
        if profile["split"] == "evaluation"
    ]
    seeds = [int(value) for value in contract["training_seeds"]]
    rows = [
        _summary(p, contract["deterministic_arm_id"], None, 1.0, 1.0)
        for p in evaluation_ids
    ]
    rows += [
        _summary(p, "cd_matd3_message", s, *full)
        for p in evaluation_ids
        for s in seeds
    ]
    rows += [
        _summary(p, "cd_matd3_no_message", s, *no_message)
        for p in evaluation_ids
        for s in seeds
    ]
    rows += [
        _summary(p, "yang_scalar_td3", s, *scalar)
        for p in evaluation_ids
        for s in seeds
    ]
    manifests = [
        _manifest(arm_id, seed)
        for arm_id in contract["learning_arm_ids"]
        for seed in seeds
    ]
    return manifests, rows


def test_contract_is_closed():
    contract = build_contract()
    profiles = contract["profiles"]
    assert len(profiles) == 8
    assert sum(p["split"] == "development" for p in profiles) == 4
    assert sum(p["split"] == "evaluation" for p in profiles) == 4
    assert all(len(p["scenarios"]) == 6 for p in profiles)
    assert contract["learning_arm_ids"] == [
        "yang_scalar_td3",
        "cd_matd3_no_message",
        "cd_matd3_message",
    ]
    assert contract["deterministic_arm_id"] == "local_neighbour_md_km2_kd2"
    assert contract["training_seeds"] == [401, 402, 403]
    assert contract["steps"] == 30
    assert contract["dt_seconds"] == 0.2
    assert contract["physical_nominal_frequency_hz"] == 60.0
    assert contract["control_nominal_frequency_hz"] == 50.0
    assert contract["action_bounds"] == [-1.0, 1.0]
    assert contract["action_slew_limit"] == 0.25
    decoder = contract["decoder"]
    assert decoder["delta_m_positive"] == 600.0
    assert decoder["delta_m_negative"] == -200.0
    assert decoder["m_lower_clamp"] == 20.0
    assert decoder["d_lower_clamp"] == 10.0
    assert contract["training_contract"]["total_interaction_steps"] == 43200
    assert contract["training_contract"]["total_training_episodes"] == 1440
    assert contract["reward_contract"]["reward_used_for_gate"] is False
    assert evaluation_record_count(contract) == 240
    assert training_run_count(contract) == 9


def test_contract_serializes_losslessly():
    contract = build_contract()
    restored = json.loads(json.dumps(contract))
    assert restored == contract
    assert contract_sha256(contract) == contract_sha256(restored)


def test_bank_is_fresh_and_disjoint_from_r399():
    contract = build_contract()
    r399 = build_r399_contract()
    fresh_ids = {str(p["profile_id"]) for p in contract["profiles"]}
    old_ids = {str(p["profile_id"]) for p in r399["profiles"]}
    assert not fresh_ids & old_ids
    old_rows = {
        (tuple(p["baseline_m0"]), tuple(p["baseline_d0"]),
         tuple(sorted(p["steady_loads"].items())))
        for p in r399["profiles"]
    }
    for profile in contract["profiles"]:
        row = (
            tuple(profile["baseline_m0"]),
            tuple(profile["baseline_d0"]),
            tuple(sorted(profile["steady_loads"].items())),
        )
        assert row not in old_rows
    for profile in contract["profiles"]:
        assert all(140.0 <= value <= 260.0 for value in profile["baseline_m0"])
        assert all(50.0 <= value <= 150.0 for value in profile["baseline_d0"])


def test_development_schedule_cycles_all_24_scenarios():
    contract = build_contract()
    order = contract["training_contract"]["development_scenario_order"]
    assert len(order) == 24
    assert len(set(order)) == 24
    development_ids = {
        str(p["profile_id"])
        for p in contract["profiles"]
        if p["split"] == "development"
    }
    for entry in order:
        profile_id, pair_kind, sign = entry.rsplit("_", 2)
        assert profile_id in development_ids
        assert pair_kind in ("common", "differential", "localized")
        assert sign in ("positive", "negative")


def test_canary_pass_requires_all_three_conditions():
    contract = build_contract()
    manifests, rows = _full_bank(contract)
    outcome = classify_canary(manifests, rows, contract=contract)
    assert outcome["classification"] == "CANARY-PASS"
    canary = outcome["canary"]
    for comparator in ("cd_matd3_no_message", "yang_scalar_td3"):
        for endpoint in ("off_diagonal_response_energy",
                         "disturbance_differential_energy"):
            assert canary["median_improvement_vs_comparators"][comparator][
                endpoint
            ] > 0.0
    assert all(canary["deterministic_reference_favorable"].values())
    assert outcome["training_authorized"] is False
    assert outcome["reward_used_for_gate"] is False


def test_canary_fail_when_full_method_loses_to_comparators():
    contract = build_contract()
    manifests, rows = _full_bank(contract, full=(1.3, 1.2))
    outcome = classify_canary(manifests, rows, contract=contract)
    assert outcome["classification"] == "CANARY-FAIL"
    assert outcome["checks"]["all_no_harm_and_action_guards"] is True


def test_canary_fail_on_common_no_harm_guard():
    contract = build_contract()
    manifests, rows = _full_bank(contract)
    for row in rows:
        if row["arm_id"] == "cd_matd3_message":
            row["common_frequency_iae_hz_s"] = 5.0
    outcome = classify_canary(manifests, rows, contract=contract)
    assert outcome["classification"] == "CANARY-FAIL"
    assert outcome.get("guard_failures")


def test_canary_invalid_on_missing_seed():
    contract = build_contract()
    manifests, rows = _full_bank(contract)
    rows = [
        row
        for row in rows
        if not (row["arm_id"] == "cd_matd3_message"
                and row["training_seed"] == 403)
    ]
    outcome = classify_canary(manifests, rows, contract=contract)
    assert outcome["classification"] == "CANARY-INVALID"
    assert outcome["checks"]["complete_bank"] is False


def test_canary_invalid_on_invalid_manifest():
    contract = build_contract()
    manifests, rows = _full_bank(contract)
    for manifest in manifests:
        if manifest["arm_id"] == "yang_scalar_td3" and manifest["training_seed"] == 401:
            manifest["convergence_diagnostics_valid"] = False
    outcome = classify_canary(manifests, rows, contract=contract)
    assert outcome["classification"] == "CANARY-INVALID"

