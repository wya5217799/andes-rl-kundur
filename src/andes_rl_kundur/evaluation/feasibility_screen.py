"""Prospective completion-only screening for controller-evaluation banks."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any


def advance_common_completion_bracket(
    *,
    lower_complete: float,
    upper_failed: float,
    tested_magnitude: float,
    completion_by_plant: Mapping[str, bool],
) -> dict[str, float | str]:
    """Advance a completion bracket only when every registered plant agrees."""
    if not lower_complete < tested_magnitude < upper_failed:
        raise ValueError("tested magnitude must be strictly inside the bracket")
    if not completion_by_plant:
        raise ValueError("at least one plant completion is required")

    completions = {bool(value) for value in completion_by_plant.values()}
    if len(completions) != 1:
        return {
            "lower_complete": float(lower_complete),
            "upper_failed": float(upper_failed),
            "classification": "PLANT-MISMATCH",
        }
    if completions == {True}:
        return {
            "lower_complete": float(tested_magnitude),
            "upper_failed": float(upper_failed),
            "classification": "COMMON-COMPLETE",
        }
    return {
        "lower_complete": float(lower_complete),
        "upper_failed": float(tested_magnitude),
        "classification": "COMMON-FAILED",
    }


def _stratum(delta_u: Mapping[str, Any]) -> tuple[str, str]:
    if len(delta_u) != 1:
        raise ValueError("each feasibility scenario must have one disturbance")
    location, raw_value = next(iter(delta_u.items()))
    value = float(raw_value)
    sign = "positive" if value > 0 else "negative" if value < 0 else "zero"
    return str(location), sign


def build_feasibility_screen_contract(
    records: Iterable[Mapping[str, Any]],
    *,
    expected_plants: Sequence[str],
    generated_bank_sha256: str,
    completion_evidence_sha256: str,
    controller_trace_count: int,
) -> dict[str, Any]:
    """Freeze a bank screen from completion evidence before controller traces.

    Every scenario remains in ``decisions``. Infeasible scenarios are also
    copied to ``retained_exclusions`` so downstream evaluation cannot silently
    discard them.
    """
    if controller_trace_count != 0:
        raise ValueError(
            "feasibility must be frozen before controller evaluation traces exist"
        )
    plants = tuple(str(plant) for plant in expected_plants)
    if not plants or len(set(plants)) != len(plants):
        raise ValueError("expected plants must be non-empty and unique")

    rows = list(records)
    if not rows:
        raise ValueError("completion evidence must contain at least one row")

    indexed: dict[tuple[str, str], Mapping[str, Any]] = {}
    scenario_order: list[str] = []
    for row in rows:
        scenario = str(row["scenario"])
        plant = str(row["plant"])
        key = (scenario, plant)
        if key in indexed:
            raise ValueError(f"duplicate completion evidence row: {key}")
        if plant not in plants:
            raise ValueError(f"unexpected plant in completion evidence: {plant}")
        if not row.get("trace_sha256"):
            raise ValueError(f"missing trace hash for completion evidence: {key}")
        indexed[key] = row
        if scenario not in scenario_order:
            scenario_order.append(scenario)

    decisions = []
    strata: dict[str, dict[str, int]] = {}
    for scenario in scenario_order:
        missing = [
            plant for plant in plants if (scenario, plant) not in indexed
        ]
        if missing:
            raise ValueError(
                f"incomplete plant evidence for {scenario}: missing {missing}"
            )
        scenario_rows = [indexed[(scenario, plant)] for plant in plants]
        delta_u = dict(scenario_rows[0]["delta_u"])
        if any(dict(row["delta_u"]) != delta_u for row in scenario_rows[1:]):
            raise ValueError(f"plant disturbance mismatch for {scenario}")
        location, sign = _stratum(delta_u)
        stratum = f"{location}|{sign}"
        completion_by_plant = {
            plant: bool(indexed[(scenario, plant)]["completed"])
            for plant in plants
        }
        feasible = all(completion_by_plant.values())
        decision = {
            "scenario": scenario,
            "delta_u": delta_u,
            "stratum": stratum,
            "completion_by_plant": completion_by_plant,
            "trace_sha256_by_plant": {
                plant: str(indexed[(scenario, plant)]["trace_sha256"])
                for plant in plants
            },
            "feasible_for_all_registered_plants": feasible,
            "disposition": (
                "controller-evaluation"
                if feasible
                else "excluded-retained"
            ),
        }
        decisions.append(decision)
        counts = strata.setdefault(
            stratum,
            {"scenario_count": 0, "excluded_scenario_count": 0},
        )
        counts["scenario_count"] += 1
        if not feasible:
            counts["excluded_scenario_count"] += 1

    retained_exclusions = [
        decision for decision in decisions
        if not decision["feasible_for_all_registered_plants"]
    ]
    scenario_count = len(decisions)
    excluded_count = len(retained_exclusions)
    return {
        "schema_version": 1,
        "contract_type": "prospective-completion-feasibility-screen",
        "generated_bank_sha256": generated_bank_sha256,
        "completion_evidence_sha256": completion_evidence_sha256,
        "expected_plants": list(plants),
        "frozen_before_controller_evaluation": True,
        "controller_trace_count_at_freeze": 0,
        "scenario_count": scenario_count,
        "excluded_scenario_count": excluded_count,
        "excluded_fraction": excluded_count / scenario_count,
        "strata": dict(sorted(strata.items())),
        "decisions": decisions,
        "retained_exclusions": retained_exclusions,
    }
