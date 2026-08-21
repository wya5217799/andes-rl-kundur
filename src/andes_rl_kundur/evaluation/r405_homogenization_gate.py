"""R405 frozen contract, gate payload aggregation, and decision tree.

Motivation
----------
R405 (route_successor_design_homogenization.md) evaluates candidate A -- the
static M/D homogenization bias -- on the eight disclosed canary profiles
against the sealed km2_kd2 deterministic reference.  This module owns the
frozen contract (profiles, arms, thresholds, sealed-reference binding), the
payload aggregation from per-profile estimator summaries, and the immutable
decision tree, so the WSL runner and the Windows-side tests share one source
of truth.

Usage
-----
    contract = build_contract()
    payload = compute_gate_payload(profile_summaries, contract=contract)
    decision = classify_r405(payload)

Failure modes
-------------
- classify_r405 never repairs payloads: validity failures return INVALID and
  guard failures return GUARD-FAIL before any endpoint ratio is considered.
- The sealed reference is bound by whole-file sha256 plus copied aggregate
  values; a mismatch is a validity failure, not a scientific outcome.

This module imports only the standard library -- no ANDES, no torch -- so it
is fully testable on the Windows host.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[3]
SEAL = ROOT / "memory" / "rounds" / "R401" / "formal_seal.json"
ENDPOINT = (
    ROOT / "results" / "research_loop" / "r402_cd_matd3_canary" / "endpoint_table.json"
)

ROUND_ID = "R405"
LINE_ID = "yang-md-decoupling-marl"
REFERENCE_ARM = "local_neighbour_md_km2_kd2"
CANDIDATE_ARM = "candidate_a_homogenized"

THRESHOLDS: dict[str, float] = {
    "cross_ratio": 0.95,
    "differential_ratio": 0.95,
    "common_no_harm": 1.03,
    "action_stress": 1.10,
    "saturation_fraction": 0.0,
}

ARMS: list[str] = [
    "zero_action",
    REFERENCE_ARM,
    CANDIDATE_ARM,
]

# The sealed R402 endpoint table stores the two endpoint energies only at
# aggregate level; the per-profile summaries carry these five guard metrics.
# All seven estimator summary keys (single frozen home; tests import this).
SUMMARY_KEYS = (
    "off_diagonal_response_energy",
    "disturbance_differential_energy",
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
)

_SEALED_SUMMARY_KEYS = (
    "common_frequency_iae_hz_s",
    "worst_unit_peak_hz",
    "worst_rocof_hz_s",
    "action_rms",
    "action_total_variation",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def build_contract() -> dict[str, Any]:
    """Build the frozen R405 contract from the R401 seal and sealed R402 table."""
    seal = _load_json(SEAL)
    profiles = seal["contract"]["profiles"]
    # Scenario ids are already profile-prefixed and unique in the R401 seal.
    scenario_ids = [
        str(scenario["scenario_id"])
        for profile in profiles
        for scenario in profile["scenarios"]
    ]
    endpoint = _load_json(ENDPOINT)
    return {
        "schema_version": 1,
        "round": ROUND_ID,
        "manuscript_line": LINE_ID,
        "authority": (
            "paper/yang_md_decoupling_marl/working/"
            "route_successor_design_homogenization.md#decision"
        ),
        "steps": 30,
        "dt_seconds": 0.2,
        "physical_nominal_frequency_hz": 60.0,
        "differential_transform": seal["contract"]["differential_transform"],
        "decoder": dict(seal["contract"]["decoder"]),
        "action_bounds": list(seal["contract"]["action_bounds"]),
        "action_slew_limit": float(seal["contract"]["action_slew_limit"]),
        "arms": list(ARMS),
        "thresholds": dict(THRESHOLDS),
        "training_authorized": False,
        "profiles": profiles,
        "scenario_ids": scenario_ids,
        "parent_seal_sha256": _sha256_file(SEAL),
        "reference": {
            "source": "results/research_loop/r402_cd_matd3_canary/endpoint_table.json",
            "sha256": _sha256_file(ENDPOINT),
            "deterministic_aggregate": dict(endpoint["deterministic_aggregate"]),
            "profile_summaries": dict(endpoint["deterministic_profile_summaries"]),
        },
        "decision_tree": {
            "order": [
                "INVALID: any validity check false",
                "GUARD-FAIL: any no-harm/stress/saturation/completion guard false",
                "NO-CROSS-EFFECT: cross_ratio > 0.95",
                "PARTIAL-A: cross_ratio <= 0.95 and differential_ratio > 0.95",
                "PASS-A: cross_ratio <= 0.95 and differential_ratio <= 0.95",
            ],
        },
    }


def contract_sha256(payload: Mapping[str, Any]) -> str:
    """Canonical whole-contract digest (stable across two identical builds)."""
    canonical = json.dumps(
        dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def compute_gate_payload(
    profile_summaries: Mapping[str, Mapping[str, dict[str, Any]]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate per-profile estimator summaries into the classifier payload.

    profile_summaries[arm_id][profile_id] uses the summarise_profile keys.
    Endpoint energies aggregate by sum over profiles (integrals); peak/RoCoF/
    stress ratios aggregate by worst-per-profile ratio.  The evaluation-
    profile reference summaries must reproduce the sealed R402 values.
    """
    spec = build_contract() if contract is None else contract
    ref_binding = spec["reference"]
    profiles = spec["profiles"]
    thresholds = spec["thresholds"]

    def require(arm: str, pid: str) -> dict[str, Any]:
        summary = profile_summaries.get(arm, {}).get(pid)
        if summary is None:
            raise ValueError(f"missing {arm} summary for {pid}")
        return summary

    def sum_key(arm: str, key: str, profile_subset: list[dict[str, Any]] | None = None) -> float:
        subset = profiles if profile_subset is None else profile_subset
        return sum(float(require(arm, str(p["profile_id"]))[key]) for p in subset)

    def worst_ratio(key: str) -> float:
        worst = 0.0
        for p in profiles:
            a = float(require(CANDIDATE_ARM, str(p["profile_id"]))[key])
            r = float(require(REFERENCE_ARM, str(p["profile_id"]))[key])
            worst = max(worst, a / r if r > 0.0 else float("inf"))
        return worst

    # Validity: sealed reference reproduction on the four evaluation profiles.
    sealed_ok = True
    for p in profiles:
        if p["split"] != "evaluation":
            continue
        pid = str(p["profile_id"])
        in_round = require(REFERENCE_ARM, pid)
        sealed = ref_binding["profile_summaries"].get(pid)
        if sealed is None:
            sealed_ok = False
            break
        for key in _SEALED_SUMMARY_KEYS:
            if abs(float(in_round[key]) - float(sealed[key])) > 1e-6 * max(
                1.0, abs(float(sealed[key]))
            ):
                sealed_ok = False
                break
        if not sealed_ok:
            break

    # Aggregate endpoints must also reproduce the sealed values.
    if sealed_ok:
        agg = ref_binding["deterministic_aggregate"]
        for key in ("off_diagonal_response_energy", "disturbance_differential_energy"):
            in_round_agg = sum(
                float(require(REFERENCE_ARM, str(p["profile_id"]))[key])
                for p in profiles
                if p["split"] == "evaluation"
            )
            if abs(in_round_agg - float(agg[key])) > 1e-6 * max(
                1.0, abs(float(agg[key]))
            ):
                sealed_ok = False
                break

    all_valid = all(
        bool(require(arm, str(p["profile_id"])).get("valid")) is True
        and int(require(arm, str(p["profile_id"])).get("record_count", 0)) == 6
        for arm in (REFERENCE_ARM, CANDIDATE_ARM)
        for p in profiles
    )

    cross_ref = sum_key(REFERENCE_ARM, "off_diagonal_response_energy")
    diff_ref = sum_key(REFERENCE_ARM, "disturbance_differential_energy")
    cross_a = sum_key(CANDIDATE_ARM, "off_diagonal_response_energy")
    diff_a = sum_key(CANDIDATE_ARM, "disturbance_differential_energy")
    eval_profiles = [p for p in profiles if p["split"] == "evaluation"]
    cross_ref_eval = sum_key(REFERENCE_ARM, "off_diagonal_response_energy", eval_profiles)
    diff_ref_eval = sum_key(REFERENCE_ARM, "disturbance_differential_energy", eval_profiles)
    cross_a_eval = sum_key(CANDIDATE_ARM, "off_diagonal_response_energy", eval_profiles)
    diff_a_eval = sum_key(CANDIDATE_ARM, "disturbance_differential_energy", eval_profiles)

    common_iae_ratio = sum_key(CANDIDATE_ARM, "common_frequency_iae_hz_s") / max(
        sum_key(REFERENCE_ARM, "common_frequency_iae_hz_s"), 1e-12
    )
    worst_peak_ratio = worst_ratio("worst_unit_peak_hz")
    worst_rocof_ratio = worst_ratio("worst_rocof_hz_s")
    action_rms_ratio = worst_ratio("action_rms")
    tv_ratio = worst_ratio("action_total_variation")

    saturation_ok = all(
        float(require(CANDIDATE_ARM, str(p["profile_id"])).get(
            "action_saturation_fraction", 0.0
        ))
        <= thresholds["saturation_fraction"]
        for p in profiles
    )

    payload = {
        "validity": {
            "sealed_match_ok": sealed_ok,
            "complete": all_valid,
            "all_rows_valid": all_valid,
        },
        "endpoints": {
            "cross_ratio": cross_a / cross_ref if cross_ref > 0.0 else float("inf"),
            "differential_ratio": diff_a / diff_ref if diff_ref > 0.0 else float("inf"),
            "cross_ratio_eval_only": (
                cross_a_eval / cross_ref_eval if cross_ref_eval > 0.0 else float("inf")
            ),
            "differential_ratio_eval_only": (
                diff_a_eval / diff_ref_eval if diff_ref_eval > 0.0 else float("inf")
            ),
        },
        "guards": {
            "common_no_harm_ok": (
                common_iae_ratio <= thresholds["common_no_harm"]
                and worst_peak_ratio <= thresholds["common_no_harm"]
                and worst_rocof_ratio <= thresholds["common_no_harm"]
            ),
            "stress_ok": (
                action_rms_ratio <= thresholds["action_stress"]
                and tv_ratio <= thresholds["action_stress"]
            ),
            "saturation_ok": saturation_ok,
            "completion_ok": all_valid,
        },
        "guard_ratios": {
            "common_iae": common_iae_ratio,
            "worst_peak": worst_peak_ratio,
            "worst_rocof": worst_rocof_ratio,
            "action_rms": action_rms_ratio,
            "action_total_variation": tv_ratio,
        },
    }
    return payload


def classify_r405(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Apply the immutable R405 decision tree to an evaluation payload.

    payload must provide:
      validity: {sealed_match_ok, complete, all_rows_valid} (bool)
      endpoints: {cross_ratio, differential_ratio} (float, ratio vs reference)
      guards: {common_no_harm_ok, stress_ok, saturation_ok, completion_ok}
    Returns {"classification": str, "reasons": [str]}.
    """
    validity = payload.get("validity", {})
    endpoints = payload.get("endpoints", {})
    guards = payload.get("guards", {})

    reasons: list[str] = []
    if not validity.get("sealed_match_ok", False):
        reasons.append("in-round km2_kd2 re-run does not reproduce the sealed values")
    if not validity.get("complete", False):
        reasons.append("bank incomplete or invalid rows present")
    if not validity.get("all_rows_valid", False):
        reasons.append("invalid rows present")
    if reasons:
        return {"classification": "INVALID", "reasons": reasons}

    if not guards.get("common_no_harm_ok", False):
        reasons.append(
            f"common no-harm ceiling exceeded ({THRESHOLDS['common_no_harm']})"
        )
    if not guards.get("stress_ok", False):
        reasons.append(
            f"action stress ceiling exceeded ({THRESHOLDS['action_stress']})"
        )
    if not guards.get("saturation_ok", False):
        reasons.append("saturation fraction above 0")
    if not guards.get("completion_ok", False):
        reasons.append("solver failure or incomplete trajectory")
    if reasons:
        return {"classification": "GUARD-FAIL", "reasons": reasons}

    cross = float(endpoints.get("cross_ratio"))
    diff = float(endpoints.get("differential_ratio"))
    if cross > THRESHOLDS["cross_ratio"]:
        return {
            "classification": "NO-CROSS-EFFECT",
            "reasons": [
                f"cross_ratio {cross} above {THRESHOLDS['cross_ratio']}: "
                "network-asymmetry dominated"
            ],
        }
    if diff > THRESHOLDS["differential_ratio"]:
        return {
            "classification": "PARTIAL-A",
            "reasons": [
                f"cross_ratio {cross} passes but differential_ratio {diff} "
                f"above {THRESHOLDS['differential_ratio']}"
            ],
        }
    return {
        "classification": "PASS-A",
        "reasons": ["both endpoint ratios at or below thresholds"],
    }