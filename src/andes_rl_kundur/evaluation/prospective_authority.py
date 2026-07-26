"""Prospective bank generation and screening for the R274 authority gate."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from andes_rl_kundur.evaluation.feasibility_screen import (
    build_feasibility_screen_contract,
)
from andes_rl_kundur.evaluation.sealed_bank import (
    CANONICAL_JSON_RULE,
    SCENARIO_BANK_SCHEMA_VERSION,
)

R274_LOCATIONS = ("PQ_0", "PQ_1", "PQ_Bus14", "PQ_Bus15")
R274_SIGNS = ("positive", "negative")
R274_SEVERITY_BOUNDS = {
    "moderate": (0.65, 0.85),
    "strong": (0.95, 1.15),
    "edge": (1.35, 1.50),
}
R274_CANDIDATE_COUNT = (
    len(R274_LOCATIONS) * len(R274_SIGNS) * len(R274_SEVERITY_BOUNDS)
)
R274_MIN_INCLUDED_COUNT = 20
R274_MAX_EXCLUDED_COUNT = 4
R274_MIN_INCLUDED_PER_LOCATION_SIGN = 2
R274_MIN_INCLUDED_EDGE_COUNT = 6
R274_MIN_MEAN_ABS_MAGNITUDE = 0.95
R274_MIN_MAX_ABS_MAGNITUDE = 1.35


def build_stratified_authority_candidates(
    *,
    seed: int,
    repository_head: str,
    generator_source_sha256: str,
) -> dict[str, Any]:
    """Return one deterministic case per location/sign/severity cell."""
    rng = np.random.default_rng(seed)
    scenarios = []
    for location in R274_LOCATIONS:
        location_slug = location.lower()
        for sign in R274_SIGNS:
            sign_multiplier = 1.0 if sign == "positive" else -1.0
            sign_slug = "pos" if sign == "positive" else "neg"
            for severity, (lower, upper) in R274_SEVERITY_BOUNDS.items():
                magnitude = round(float(rng.uniform(lower, upper)), 4)
                scenarios.append(
                    {
                        "name": (
                            f"cand_{location_slug}_{sign_slug}_{severity}"
                        ),
                        "delta_u": {
                            location: sign_multiplier * magnitude,
                        },
                        "location": location,
                        "sign": sign,
                        "severity": severity,
                    }
                )
    permutation = rng.permutation(len(scenarios))
    scenarios = [scenarios[int(index)] for index in permutation]
    return {
        "schema_version": SCENARIO_BANK_SCHEMA_VERSION,
        "generator": (
            "andes_rl_kundur.evaluation.prospective_authority."
            "build_stratified_authority_candidates"
        ),
        "generator_arguments": {
            "n": R274_CANDIDATE_COUNT,
            "seed": seed,
            "include_anchors": False,
        },
        "generator_source_sha256": generator_source_sha256,
        "repository_head": repository_head,
        "serialization": CANONICAL_JSON_RULE,
        "scenario_count": len(scenarios),
        "stratification": {
            "locations": list(R274_LOCATIONS),
            "signs": list(R274_SIGNS),
            "severity_bounds_abs_system_pu": {
                severity: [lower, upper]
                for severity, (lower, upper) in R274_SEVERITY_BOUNDS.items()
            },
            "cases_per_location_sign_severity": 1,
            "order": "single seeded permutation after stratified sampling",
        },
        "scenarios": scenarios,
    }


def _absolute_magnitude(scenario: Mapping[str, Any]) -> float:
    return abs(float(next(iter(scenario["delta_u"].values()))))


def audit_zero_support_screen_record(
    record: Mapping[str, Any],
    *,
    trace_sha256: str,
) -> dict[str, Any]:
    """Reduce a raw baseline trace to completion and frozen-physics evidence."""
    traces = list(record.get("traces", []))

    def flattened(field: str) -> np.ndarray:
        return np.asarray(
            [
                value
                for step in traces
                for value in step.get(field, [])
            ],
            dtype=float,
        )

    requested = flattened("bess_requested_power_system_pu")
    commanded = flattened("bess_commanded_power_system_pu")
    actual = flattened("bess_actual_power_system_pu")
    soc = flattened("bess_soc")
    m_values = flattened("M_es")
    d_values = flattened("D_es")
    violations = [
        violation
        for step in traces
        for violation in step.get("bess_constraint_violations", [])
    ]

    def max_abs(values: np.ndarray) -> float:
        return float(np.max(np.abs(values))) if values.size else 0.0

    m_unique = sorted(set(m_values.tolist()))
    d_unique = sorted(set(d_values.tolist()))
    physical_valid = (
        record.get("controller") == "zero_support"
        and bool(traces)
        and max_abs(requested) == 0.0
        and max_abs(commanded) == 0.0
        and max_abs(actual) == 0.0
        and bool(soc.size)
        and float(np.min(soc)) == 0.5
        and float(np.max(soc)) == 0.5
        and m_unique == [200.0]
        and d_unique == [100.0]
        and not violations
    )
    return {
        "scenario": str(record["scenario"]),
        "plant": "storage_zero",
        "delta_u": dict(record["delta_u"]),
        "completed": bool(record["completed"]),
        "tds_failed": bool(record["tds_failed"]),
        "n_steps": int(record["n_steps"]),
        "requested_steps": int(record["requested_steps"]),
        "physical_valid": physical_valid,
        "max_abs_requested_power": max_abs(requested),
        "max_abs_commanded_power": max_abs(commanded),
        "max_abs_actual_power": max_abs(actual),
        "min_soc": float(np.min(soc)) if soc.size else None,
        "max_soc": float(np.max(soc)) if soc.size else None,
        "m_unique": m_unique,
        "d_unique": d_unique,
        "constraint_violation_count": len(violations),
        "trace_sha256": trace_sha256,
    }


def assess_screened_authority_bank(
    candidate_bank: Mapping[str, Any],
    records: Iterable[Mapping[str, Any]],
    *,
    generated_bank_sha256: str,
    completion_evidence_sha256: str,
    controller_trace_count: int,
) -> dict[str, Any]:
    """Freeze the all-and-only feasible subset and its nontriviality gate."""
    scenarios = list(candidate_bank["scenarios"])
    rows = list(records)
    by_name = {str(row["scenario"]): row for row in rows}
    candidate_names = [str(scenario["name"]) for scenario in scenarios]
    if len(by_name) != len(rows) or set(by_name) != set(candidate_names):
        raise ValueError("screen rows must match candidate scenarios exactly")
    if any(str(row.get("plant")) != "storage_zero" for row in rows):
        raise ValueError("screen evidence must use the storage_zero plant")

    row_decisions = []
    contract_rows = []
    included_scenarios = []
    for scenario in scenarios:
        row = by_name[str(scenario["name"])]
        if dict(row["delta_u"]) != dict(scenario["delta_u"]):
            raise ValueError(f"screen disturbance mismatch: {scenario['name']}")
        complete = (
            bool(row["completed"])
            and not bool(row["tds_failed"])
            and int(row["n_steps"]) == int(row["requested_steps"]) == 300
        )
        physical_valid = bool(row["physical_valid"])
        eligible = complete and physical_valid
        reasons = []
        if not complete:
            reasons.append("incomplete-or-tds-failed")
        if not physical_valid:
            reasons.append("zero-support-physical-audit-failed")
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
                "plant": "storage_zero",
                "delta_u": dict(scenario["delta_u"]),
                "completed": eligible,
                "trace_sha256": str(row["trace_sha256"]),
            }
        )
        if eligible:
            included_scenarios.append(dict(scenario))

    feasibility_contract = build_feasibility_screen_contract(
        contract_rows,
        expected_plants=("storage_zero",),
        generated_bank_sha256=generated_bank_sha256,
        completion_evidence_sha256=completion_evidence_sha256,
        controller_trace_count=controller_trace_count,
    )

    generated_location_sign = Counter(
        f"{scenario['location']}|{scenario['sign']}"
        for scenario in scenarios
    )
    generated_severity = Counter(
        str(scenario["severity"]) for scenario in scenarios
    )
    generated_magnitudes = [
        _absolute_magnitude(scenario) for scenario in scenarios
    ]
    included_location_sign = Counter(
        f"{scenario['location']}|{scenario['sign']}"
        for scenario in included_scenarios
    )
    included_magnitudes = [
        _absolute_magnitude(scenario) for scenario in included_scenarios
    ]
    included_edge_count = sum(
        scenario["severity"] == "edge"
        for scenario in included_scenarios
    )
    expected_location_sign = {
        f"{location}|{sign}"
        for location in R274_LOCATIONS
        for sign in R274_SIGNS
    }
    included_mean = (
        float(np.mean(included_magnitudes)) if included_magnitudes else 0.0
    )
    included_max = max(included_magnitudes, default=0.0)
    generated_mean = float(np.mean(generated_magnitudes))
    generated_max = max(generated_magnitudes, default=0.0)

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
        "included_count_ge_20": (
            len(included_scenarios) >= R274_MIN_INCLUDED_COUNT
        ),
        "excluded_count_le_4": (
            len(scenarios) - len(included_scenarios)
            <= R274_MAX_EXCLUDED_COUNT
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
            if decision["scenario"]
            in {scenario["name"] for scenario in included_scenarios}
        ),
        "controller_trace_count_zero_at_freeze": controller_trace_count == 0,
    }
    classification = "PASS" if all(guards.values()) else "INVALID"
    formal_bank = {
        "schema_version": SCENARIO_BANK_SCHEMA_VERSION,
        "generator": (
            "andes_rl_kundur.evaluation.prospective_authority."
            "assess_screened_authority_bank"
        ),
        "generator_arguments": {
            "n": len(included_scenarios),
            "seed": candidate_bank["generator_arguments"]["seed"],
            "include_anchors": False,
        },
        "generator_source_sha256": candidate_bank[
            "generator_source_sha256"
        ],
        "repository_head": candidate_bank["repository_head"],
        "serialization": CANONICAL_JSON_RULE,
        "scenario_count": len(included_scenarios),
        "source_candidate_bank_sha256": generated_bank_sha256,
        "completion_evidence_sha256": completion_evidence_sha256,
        "selection_rule": "all-and-only eligible zero-support screen rows",
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
