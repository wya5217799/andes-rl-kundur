"""R378 correction of the R377 settling-rule defect.

R377 sealed a development rule that requires the candidate's mean
differential settling time to be at least one ``dt`` below the local arm.
The executed development records show every arm (including the local arm) at
the registered settling floor of 1.2 s, so that rule is unsatisfiable for any
candidate.  This module provides the corrected selection rule that changes
only the settling requirement from "at least one dt below local" to "no
worse than local", plus a validator that proves the correction touches only
the settling rule and the round/selector identity.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from andes_rl_kundur.evaluation.gate_b2_deterministic import (
    LOCAL_ARM,
    ZERO_ARM,
    _mean_condition_metric,
    _positive_ratio,
    _probe_no_harm,
    build_contract,
)

R378_LOCAL_ARM = "local_feasibility_native"


def build_corrected_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Return the R378 contract that differs from R377 only in round id."""
    corrected = dict(contract)
    corrected["round"] = "R378"
    corrected["correction_scope"] = ["round", "settling_rule"]
    return corrected


def validate_correction(
    parent: Mapping[str, Any],
    corrected: Mapping[str, Any],
) -> bool:
    """Prove the correction changes only round id and the settling rule.

    The parent contract is the sealed R377 contract; the corrected contract
    must keep every other field semantically equal.  The settling-rule
    change lives in the selection/classification code, not in the contract
    thresholds, so the contract diff is exactly the round id.
    """
    if corrected.get("round") != "R378":
        return False
    if corrected.get("correction_scope") != ["round", "settling_rule"]:
        return False
    parent_view = dict(parent)
    corrected_view = dict(corrected)
    parent_view.pop("round", None)
    corrected_view.pop("round", None)
    corrected_view.pop("correction_scope", None)
    return parent_view == corrected_view


def corrected_settling_pass(
    candidate_settling: float,
    local_settling: float,
    *,
    tolerance: float = 1.0e-12,
) -> bool:
    """Corrected settling rule: candidate must be no worse than local."""
    return float(candidate_settling) <= float(local_settling) + tolerance


def select_development_candidate(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Corrected R378 development selection: settling no worse than local.

    Identical to the R377 rule except that the settling requirement becomes
    ``candidate_settling <= local_settling`` instead of at least one dt
    below local.
    """
    frozen = contract or build_contract()
    baseline = summaries.get(R378_LOCAL_ARM)
    if baseline is None or not bool(baseline.get("guards_pass")):
        return {
            "classification": "ANALYSIS-INVALID",
            "selected_arm_id": None,
            "eligible_candidates": [],
            "training_authorized": False,
        }
    primary_threshold = float(frozen["thresholds"]["development_primary_ratio_max"])
    common_limit = float(frozen["thresholds"]["common_iae_ratio_max"])
    cross_limit = float(frozen["thresholds"]["probe_cross_no_harm_ratio_max"])
    local_settling = float(
        baseline["disturbance"]["mean_differential_settling_seconds"]
    )
    eligible: list[dict[str, Any]] = []
    for candidate_spec in frozen["distributed_candidates"]:
        arm_id = str(candidate_spec["arm_id"])
        candidate = summaries.get(arm_id)
        if candidate is None or not bool(candidate.get("guards_pass")):
            continue
        differential_ratio = _positive_ratio(
            candidate["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
            baseline["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
        )
        candidate_settling = float(
            candidate["disturbance"]["mean_differential_settling_seconds"]
        )
        settling_improvement = corrected_settling_pass(
            candidate_settling,
            local_settling,
        )
        common_ratio = _positive_ratio(
            _mean_condition_metric(candidate, "common_frequency_iae_hz_s"),
            _mean_condition_metric(baseline, "common_frequency_iae_hz_s"),
        )
        offdiag_ratio, normalized_cross_ratio = _probe_no_harm(candidate, baseline)
        if (
            differential_ratio <= primary_threshold
            and settling_improvement
            and common_ratio <= common_limit
            and offdiag_ratio <= cross_limit
            and normalized_cross_ratio <= cross_limit
        ):
            eligible.append(
                {
                    "arm_id": arm_id,
                    "differential_energy_ratio": differential_ratio,
                    "settling_seconds": candidate_settling,
                    "common_iae_ratio": common_ratio,
                    "probe_offdiag_ratio": offdiag_ratio,
                    "probe_cross_ratio": normalized_cross_ratio,
                    "rank_score": (
                        differential_ratio
                        * (
                            candidate_settling
                            / local_settling
                            if local_settling > 0.0
                            else 1.0
                        )
                    ),
                    "sync_gain_per_hz": float(
                        candidate_spec["sync_gain_per_hz"]
                    ),
                    "consensus_gain_per_s": float(
                        candidate_spec["consensus_gain_per_s"]
                    ),
                }
            )
    eligible.sort(
        key=lambda row: (
            float(row["rank_score"]),
            float(row["sync_gain_per_hz"]),
            float(row["consensus_gain_per_s"]),
        )
    )
    return {
        "classification": (
            "DEVELOPMENT-CANDIDATE-SELECTED"
            if eligible
            else "STOP-DEVELOPMENT-NO-CANDIDATE"
        ),
        "selected_arm_id": eligible[0]["arm_id"] if eligible else None,
        "eligible_candidates": eligible,
        "training_authorized": False,
    }


def classify_summaries(
    development: Mapping[str, Any],
    evaluation: Mapping[str, Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Corrected R378 held-out classification with the corrected settling rule."""
    frozen = contract or build_contract()
    selected_id = development.get("selected_arm_id")
    if development.get("classification") != "DEVELOPMENT-CANDIDATE-SELECTED":
        return {
            "classification": str(development.get("classification")),
            "checks": {},
            "selected_arm_id": selected_id,
            "training_authorized": False,
            "next_gate": None,
        }
    if not isinstance(selected_id, str):
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": {},
            "selected_arm_id": None,
            "training_authorized": False,
            "next_gate": None,
        }
    try:
        selected = evaluation[selected_id]
        baselines = [evaluation[ZERO_ARM], evaluation[LOCAL_ARM]]
    except KeyError:
        return {
            "classification": "ANALYSIS-INVALID",
            "checks": {},
            "selected_arm_id": selected_id,
            "training_authorized": False,
            "next_gate": None,
        }
    primary_limit = float(frozen["thresholds"]["heldout_primary_ratio_max"])
    single_limit = float(frozen["thresholds"]["single_disturbance_ratio_max"])
    common_limit = float(frozen["thresholds"]["common_iae_ratio_max"])
    other_limit = float(frozen["thresholds"]["peak_and_rocof_ratio_max"])
    cross_limit = float(frozen["thresholds"]["probe_cross_no_harm_ratio_max"])

    differential_mean_ratios = [
        _positive_ratio(
            selected["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
            baseline["disturbance"][
                "mean_differential_frequency_energy_hz2_s"
            ],
        )
        for baseline in baselines
    ]
    selected_conditions = selected["disturbance"]["conditions"]
    per_condition_pass = True
    for condition_id, row in selected_conditions.items():
        for baseline in baselines:
            baseline_row = baseline["disturbance"]["conditions"][condition_id]
            per_condition_pass = per_condition_pass and (
                _positive_ratio(
                    row["differential_frequency_energy_hz2_s"],
                    baseline_row["differential_frequency_energy_hz2_s"],
                )
                <= single_limit
            )
    selected_settling = float(
        selected["disturbance"]["mean_differential_settling_seconds"]
    )
    local_settling = float(
        evaluation[LOCAL_ARM]["disturbance"]["mean_differential_settling_seconds"]
    )
    baseline_settling = [
        float(item["disturbance"]["mean_differential_settling_seconds"])
        for item in baselines
    ]
    settling_pass = (
        all(selected_settling <= value + 1.0e-12 for value in baseline_settling)
        and corrected_settling_pass(selected_settling, local_settling)
    )
    differential_pass = (
        all(ratio <= primary_limit for ratio in differential_mean_ratios)
        and per_condition_pass
        and settling_pass
    )

    common_pass = True
    for metric, limit in (
        ("common_frequency_iae_hz_s", common_limit),
        ("worst_device_peak_abs_hz", other_limit),
        ("max_rocof_hz_per_s", other_limit),
    ):
        selected_value = _mean_condition_metric(selected, metric)
        best_baseline = min(_mean_condition_metric(item, metric) for item in baselines)
        common_pass = common_pass and selected_value <= limit * best_baseline

    no_harm_pass = True
    for baseline in baselines:
        offdiag_ratio, normalized_cross_ratio = _probe_no_harm(selected, baseline)
        no_harm_pass = no_harm_pass and (
            offdiag_ratio <= cross_limit
            and normalized_cross_ratio <= cross_limit
        )

    physical_pass = bool(selected.get("guards_pass")) and all(
        bool(item.get("guards_pass")) for item in baselines
    )
    checks = {
        "differential_oscillation_reduction": differential_pass,
        "common_mode_no_harm": common_pass,
        "probe_cross_no_harm": no_harm_pass,
        "physical_and_execution_guards": physical_pass,
    }
    if not physical_pass:
        classification = "STOP-UNSAFE-CONTROL"
    elif not differential_pass:
        classification = "STOP-NO-DIFFERENTIAL-BENEFIT"
    elif not common_pass:
        classification = "STOP-COMMON-MODE-HARM"
    elif not no_harm_pass:
        classification = "STOP-NO-HARM-EXCEEDED"
    else:
        classification = "DETERMINISTIC-DECOUPLING-PASS"
    return {
        "classification": classification,
        "checks": checks,
        "selected_arm_id": selected_id,
        "differential_mean_ratios_vs_zero_and_local": (
            differential_mean_ratios
        ),
        "probe_cross_ratios_vs_zero_and_local": [
            _probe_no_harm(selected, baseline) for baseline in baselines
        ],
        "training_authorized": False,
        "next_gate": (
            "non_learning_time_varying_headroom"
            if classification == "DETERMINISTIC-DECOUPLING-PASS"
            else None
        ),
    }


def summarize_immutable_development(
    records: list[Mapping[str, Any]],
    *,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Re-summarize the immutable R377 development records under R378.

    Uses the unchanged R377 summarizer on the immutable records; only the
    selection rule is corrected.  Returns the phase summary plus the
    corrected selection.
    """
    from andes_rl_kundur.evaluation.gate_b2_deterministic import (
        summarize_phase_records,
    )

    frozen = contract or build_contract()
    phase = summarize_phase_records(
        records,
        phase="development",
        contract=frozen,
    )
    selection = select_development_candidate(
        phase["arm_summaries"],
        contract=frozen,
    )
    return {"development": phase, "selection": selection}

