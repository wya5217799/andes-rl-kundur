"""R292-specific aggregation for q0 completion and physical-screen records.

The historical prospective-authority aggregator is intentionally bound to a
storage-zero plant.  R292 freezes a different q0 plant, so this module applies
the same already-registered bank-balance and nontriviality guards while naming
only the R292 physical contract.  It consumes reduced audit rows and never
reads controller frequency-performance endpoints.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.feasibility_screen import (
    build_feasibility_screen_contract,
)
from andes_rl_kundur.evaluation.prospective_authority import (
    R274_CANDIDATE_COUNT,
    R274_LOCATIONS,
    R274_MAX_EXCLUDED_COUNT,
    R274_MIN_INCLUDED_COUNT,
    R274_MIN_INCLUDED_EDGE_COUNT,
    R274_MIN_INCLUDED_PER_LOCATION_SIGN,
    R274_MIN_MAX_ABS_MAGNITUDE,
    R274_MIN_MEAN_ABS_MAGNITUDE,
    R274_SIGNS,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    CANONICAL_JSON_RULE,
    SCENARIO_BANK_SCHEMA_VERSION,
)

R292_Q0_SCREEN_PLANT = "r292_q0_common_pulse_plus_droop_pi"


def _absolute_magnitude(scenario: Mapping[str, Any]) -> float:
    return abs(float(next(iter(scenario["delta_u"].values()))))


def assess_r292_screened_bank(
    candidate_bank: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
    *,
    generated_bank_sha256: str,
    completion_evidence_sha256: str,
    controller_trace_count: int,
) -> dict[str, Any]:
    """Freeze all and only eligible R292 q0 rows under registered guards."""
    scenarios = list(candidate_bank["scenarios"])
    rows = list(records)
    by_name = {str(row["scenario"]): row for row in rows}
    candidate_names = [str(scenario["name"]) for scenario in scenarios]
    if len(by_name) != len(rows) or set(by_name) != set(candidate_names):
        raise ValueError("screen rows must match candidate scenarios exactly")
    if any(str(row.get("plant")) != R292_Q0_SCREEN_PLANT for row in rows):
        raise ValueError("screen evidence must use the R292 q0 plant")
    if any(row.get("performance_endpoints_inspected") is not False for row in rows):
        raise ValueError("R292 q0 screen rows must exclude performance endpoints")

    row_decisions: list[dict[str, Any]] = []
    contract_rows: list[dict[str, Any]] = []
    included_scenarios: list[dict[str, Any]] = []
    for scenario in scenarios:
        row = by_name[str(scenario["name"])]
        if dict(row["delta_u"]) != dict(scenario["delta_u"]):
            raise ValueError(f"screen disturbance mismatch: {scenario['name']}")
        complete = bool(
            row["completed"]
            and not row["tds_failed"]
            and int(row["n_steps"]) == int(row["requested_steps"]) == 300
        )
        physical_valid = bool(row["physical_valid"])
        eligible = complete and physical_valid
        reasons = []
        if not complete:
            reasons.append("incomplete-or-tds-failed")
        if not physical_valid:
            reasons.append("r292-q0-physical-audit-failed")
        row_decisions.append(
            {
                "scenario": scenario["name"],
                "location": scenario["location"],
                "sign": scenario["sign"],
                "severity": scenario["severity"],
                "delta_u": dict(scenario["delta_u"]),
                "eligible": eligible,
                "reasons": reasons,
                "trace_sha256": str(row["trace_sha256"]),
            }
        )
        contract_rows.append(
            {
                "scenario": scenario["name"],
                "plant": R292_Q0_SCREEN_PLANT,
                "delta_u": dict(scenario["delta_u"]),
                "completed": eligible,
                "trace_sha256": str(row["trace_sha256"]),
            }
        )
        if eligible:
            included_scenarios.append(dict(scenario))

    feasibility_contract = build_feasibility_screen_contract(
        contract_rows,
        expected_plants=(R292_Q0_SCREEN_PLANT,),
        generated_bank_sha256=generated_bank_sha256,
        completion_evidence_sha256=completion_evidence_sha256,
        controller_trace_count=controller_trace_count,
    )

    generated_location_sign = Counter(
        f"{scenario['location']}|{scenario['sign']}" for scenario in scenarios
    )
    generated_severity = Counter(str(scenario["severity"]) for scenario in scenarios)
    generated_magnitudes = [_absolute_magnitude(scenario) for scenario in scenarios]
    included_location_sign = Counter(
        f"{scenario['location']}|{scenario['sign']}"
        for scenario in included_scenarios
    )
    included_magnitudes = [
        _absolute_magnitude(scenario) for scenario in included_scenarios
    ]
    included_edge_count = sum(
        scenario["severity"] == "edge" for scenario in included_scenarios
    )
    expected_location_sign = {
        f"{location}|{sign}" for location in R274_LOCATIONS for sign in R274_SIGNS
    }
    included_mean = (
        float(np.mean(included_magnitudes)) if included_magnitudes else 0.0
    )
    included_max = max(included_magnitudes, default=0.0)
    generated_mean = float(np.mean(generated_magnitudes))
    generated_max = max(generated_magnitudes, default=0.0)
    included_names = {scenario["name"] for scenario in included_scenarios}

    guards = {
        "candidate_count_24": len(scenarios) == R274_CANDIDATE_COUNT,
        "generated_location_sign_balance": (
            set(generated_location_sign) == expected_location_sign
            and all(value == 3 for value in generated_location_sign.values())
        ),
        "generated_severity_balance": generated_severity
        == Counter({"moderate": 8, "strong": 8, "edge": 8}),
        "generated_mean_abs_magnitude_ge_0_95": (
            generated_mean >= R274_MIN_MEAN_ABS_MAGNITUDE
        ),
        "generated_max_abs_magnitude_ge_1_35": (
            generated_max >= R274_MIN_MAX_ABS_MAGNITUDE
        ),
        "included_count_ge_20": len(included_scenarios) >= R274_MIN_INCLUDED_COUNT,
        "excluded_count_le_4": (
            len(scenarios) - len(included_scenarios) <= R274_MAX_EXCLUDED_COUNT
        ),
        "each_location_sign_included_ge_2": (
            set(included_location_sign) == expected_location_sign
            and all(
                value >= R274_MIN_INCLUDED_PER_LOCATION_SIGN
                for value in included_location_sign.values()
            )
        ),
        "included_edge_count_ge_6": (
            included_edge_count >= R274_MIN_INCLUDED_EDGE_COUNT
        ),
        "included_mean_abs_magnitude_ge_0_95": (
            included_mean >= R274_MIN_MEAN_ABS_MAGNITUDE
        ),
        "included_max_abs_magnitude_ge_1_35": (
            included_max >= R274_MIN_MAX_ABS_MAGNITUDE
        ),
        "included_rows_complete_and_physical_valid": all(
            decision["eligible"]
            for decision in row_decisions
            if decision["scenario"] in included_names
        ),
        "controller_trace_count_zero_at_freeze": controller_trace_count == 0,
    }
    classification = "PASS" if all(guards.values()) else "INVALID"
    formal_bank = {
        "schema_version": SCENARIO_BANK_SCHEMA_VERSION,
        "generator": (
            "andes_rl_kundur.evaluation.r292_screen_bank."
            "assess_r292_screened_bank"
        ),
        "generator_arguments": {
            "n": len(included_scenarios),
            "seed": candidate_bank["generator_arguments"]["seed"],
            "include_anchors": False,
        },
        "generator_source_sha256": candidate_bank["generator_source_sha256"],
        "repository_head": candidate_bank["repository_head"],
        "serialization": CANONICAL_JSON_RULE,
        "scenario_count": len(included_scenarios),
        "source_candidate_bank_sha256": generated_bank_sha256,
        "completion_evidence_sha256": completion_evidence_sha256,
        "selection_rule": "all-and-only eligible R292 q0 physical-screen rows",
        "scenarios": included_scenarios,
    }
    return {
        "decision": {
            "classification": classification,
            "guards": guards,
            "reason": (
                "all prospective screen and nontriviality guards pass"
                if classification == "PASS"
                else "one or more prospective screen/nontriviality guards failed"
            ),
        },
        "generated_nontriviality": {
            "mean_abs_magnitude": generated_mean,
            "max_abs_magnitude": generated_max,
            "location_sign_counts": dict(sorted(generated_location_sign.items())),
            "severity_counts": dict(sorted(generated_severity.items())),
        },
        "included_nontriviality": {
            "scenario_count": len(included_scenarios),
            "excluded_count": len(scenarios) - len(included_scenarios),
            "excluded_fraction": (
                (len(scenarios) - len(included_scenarios)) / len(scenarios)
            ),
            "mean_abs_magnitude": included_mean,
            "max_abs_magnitude": included_max,
            "edge_count": included_edge_count,
            "location_sign_counts": dict(sorted(included_location_sign.items())),
        },
        "row_decisions": row_decisions,
        "feasibility_contract": feasibility_contract,
        "formal_bank": formal_bank,
    }
