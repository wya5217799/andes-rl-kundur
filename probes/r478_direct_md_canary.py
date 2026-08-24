"""R478 Yang-line direct-M/D transport-canary classifier.

This question-specific probe classifies exactly the registered 12-record
``dev_a`` zero-versus-deterministic-comparator bank. It never executes ANDES,
opens training, or produces formal evidence. Its only routing role is to stop
on invalid input or a qualitative comparator shift, or to permit the next
energy-port canary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

import numpy as np

DIRECT_CANARY_PROFILE = "dev_a"
DIRECT_CANARY_ARMS = ("zero", "local_neighbour_md_km2_kd2")


def normalize_system_base_direct_telemetry(
    records: Sequence[Mapping[str, Any]],
    *,
    parameter_card: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Return copies whose legacy system-base M/D telemetry is device-base.

    The R416 physical job writer predates the corrected environment boundary:
    it reads ``GENCLS.M/D`` directly (system base), while its identity and
    ``delta_M/delta_D`` fields are device-base.  The frozen Yang parameter card
    supplies the only conversion used here.  Raw records are never mutated,
    and a normalization marker prevents accidental double conversion.
    """
    system_mva = float(parameter_card["system_base_mva"])
    device = parameter_card["devices"]["vsg_1_to_4"]
    device_mva = float(device["sn_mva"])
    if parameter_card.get("telemetry_base") != (
        "device (info M_es/D_es); invariant: equals ANDES readback converted "
        "to device"
    ):
        raise ValueError("parameter card does not freeze device-base telemetry")
    if system_mva <= 0.0 or device_mva <= 0.0:
        raise ValueError("parameter-card bases must be positive")

    scale = system_mva / device_mva
    normalized: list[dict[str, Any]] = []
    for source in records:
        if "telemetry_normalization" in source:
            raise ValueError("direct record is already telemetry-normalized")
        record = deepcopy(dict(source))
        for step in record.get("steps", []):
            step["M_es"] = (
                np.asarray(step["M_es"], dtype=float) * scale
            ).tolist()
            step["D_es"] = (
                np.asarray(step["D_es"], dtype=float) * scale
            ).tolist()
        record["telemetry_normalization"] = {
            "source_base": "ANDES system",
            "target_base": "device",
            "system_base_mva": system_mva,
            "device_mva": device_mva,
            "scale": scale,
        }
        normalized.append(record)
    return normalized


def classify_direct_md_canary(
    records: Sequence[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify the frozen 12-record direct-M/D route canary.

    This is the registered ``dev_a`` entrypoint.  The profile-general helper
    is used only by explicitly named successor scratch confirmations.
    """
    return classify_direct_md_profile(
        records,
        profile_id=DIRECT_CANARY_PROFILE,
        contract=contract,
        pass_next_step="open energy-port canary only",
        shift_next_step="stop; open direct-M/D deterministic formal bank only",
    )


def classify_direct_md_profile(
    records: Sequence[Mapping[str, Any]],
    *,
    profile_id: str,
    contract: Mapping[str, Any] | None = None,
    pass_next_step: str = "stop; await cross-profile stage verdict",
    shift_next_step: str = "stop; redesign direct-M/D route",
) -> dict[str, Any]:
    """Classify one complete 12-record zero/comparator profile.

    Formal evaluation-arm action-stress guards are deliberately not reused:
    their reference is the already selected deterministic comparator, so they
    have no non-circular reference in this zero-versus-comparator check.
    Instead, the comparator must pass the registered absolute mapping, bound,
    slew, saturation, nonconstant-action, and per-VSG-dispersion checks.
    """
    from andes_rl_kundur.evaluation.md_decoupling_headroom import (
        build_contract,
        summarise_profile,
    )

    spec = build_contract() if contract is None else contract
    profile = next(
        (
            row
            for row in spec["profiles"]
            if str(row["profile_id"]) == profile_id
        ),
        None,
    )
    expected_scenarios = (
        set()
        if profile is None
        else {str(row["scenario_id"]) for row in profile["scenarios"]}
    )
    by_arm: dict[str, list[Mapping[str, Any]]] = {
        arm_id: [] for arm_id in DIRECT_CANARY_ARMS
    }
    observed_keys: set[tuple[str, str]] = set()
    duplicate = False
    for record in records:
        arm_id = str(record.get("arm_id", ""))
        scenario_id = str(record.get("scenario_id", ""))
        key = (arm_id, scenario_id)
        duplicate = duplicate or key in observed_keys
        observed_keys.add(key)
        if arm_id in by_arm:
            by_arm[arm_id].append(record)
    expected_keys = {
        (arm_id, scenario_id)
        for arm_id in DIRECT_CANARY_ARMS
        for scenario_id in expected_scenarios
    }
    complete = (
        profile is not None
        and len(records) == 12
        and not duplicate
        and observed_keys == expected_keys
        and all(
            str(record.get("profile_id", "")) == profile_id
            for record in records
        )
    )
    base = {
        "schema_version": 1,
        "round": str(spec.get("round", "")),
        "manuscript_line": str(spec.get("manuscript_line", "")),
        "profile_id": profile_id,
        "arms": list(DIRECT_CANARY_ARMS),
        "record_count": len(records),
        "training_authorized": False,
        "formal_evidence": False,
    }
    if not complete:
        return {
            **base,
            "classification": "ANALYSIS-INVALID",
            "checks": {"complete_registered_12_record_bank": False},
            "next_step": "stop; repair canary integrity before physical inference",
        }

    try:
        summaries = {
            arm_id: summarise_profile(by_arm[arm_id], contract=spec)
            for arm_id in DIRECT_CANARY_ARMS
        }
    except (TypeError, ValueError) as exc:
        return {
            **base,
            "classification": "ANALYSIS-INVALID",
            "checks": {
                "complete_registered_12_record_bank": True,
                "summaries_valid": False,
            },
            "error": f"{type(exc).__name__}: {exc}",
            "next_step": "stop; repair canary integrity before physical inference",
        }

    zero = summaries[DIRECT_CANARY_ARMS[0]]
    candidate = summaries[DIRECT_CANARY_ARMS[1]]
    summaries_valid = bool(zero["valid"] and candidate["valid"])
    if not summaries_valid:
        return {
            **base,
            "classification": "ANALYSIS-INVALID",
            "checks": {
                "complete_registered_12_record_bank": True,
                "summaries_valid": False,
            },
            "summaries": summaries,
            "next_step": "stop; repair canary integrity before physical inference",
        }

    thresholds = spec["thresholds"]
    zero_off = float(zero["off_diagonal_response_energy"])
    zero_differential = float(zero["disturbance_differential_energy"])
    positive_reference = min(zero_off, zero_differential) > 0.0
    if not positive_reference:
        return {
            **base,
            "classification": "ANALYSIS-INVALID",
            "checks": {
                "complete_registered_12_record_bank": True,
                "summaries_valid": True,
                "positive_zero_reference": False,
            },
            "summaries": summaries,
            "next_step": "stop; repair canary integrity before physical inference",
        }

    off_ratio = float(candidate["off_diagonal_response_energy"]) / zero_off
    differential_ratio = (
        float(candidate["disturbance_differential_energy"]) / zero_differential
    )
    maximum_common_harm = float(thresholds["maximum_common_harm"])
    common_limit = 1.0 + maximum_common_harm
    checks = {
        "complete_registered_12_record_bank": True,
        "summaries_valid": True,
        "positive_zero_reference": True,
        "off_diagonal_ratio_at_most_0p95": off_ratio <= 0.95,
        "differential_ratio_at_most_0p95": differential_ratio <= 0.95,
        "common_frequency_no_harm": float(candidate["common_frequency_iae_hz_s"])
        <= common_limit * float(zero["common_frequency_iae_hz_s"]) + 1.0e-15,
        "worst_peak_no_harm": float(candidate["worst_unit_peak_hz"])
        <= common_limit * float(zero["worst_unit_peak_hz"]) + 1.0e-15,
        "rocof_no_harm": float(candidate["worst_rocof_hz_s"])
        <= common_limit * float(zero["worst_rocof_hz_s"]) + 1.0e-15,
        "saturation_budget": float(candidate["action_saturation_fraction"])
        <= float(thresholds["maximum_action_saturation_fraction"]),
        "nonconstant_action": float(candidate["minimum_record_total_variation"])
        > float(thresholds["nonconstant_action_variation_floor"]),
        "independent_per_vsg_action": float(
            candidate["minimum_record_action_row_dispersion"]
        )
        > float(thresholds["independent_action_dispersion_floor"]),
    }
    passed = all(checks.values())
    return {
        **base,
        "classification": "DIRECT-CANARY-PASS" if passed else "DIRECT-CANARY-SHIFT",
        "checks": checks,
        "metrics": {
            "off_diagonal_ratio_to_zero": off_ratio,
            "differential_ratio_to_zero": differential_ratio,
        },
        "summaries": summaries,
        "next_step": (
            pass_next_step
            if passed
            else shift_next_step
        ),
    }
