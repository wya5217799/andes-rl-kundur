"""Conclusion-affecting seams for the R363 common-channel headroom gate.

The probe rebuilds the exact R358 exposed development cases, extends the
action basis with the frozen common residual-power channel, solves the same
physical joint-endpoint QP per case over the four-channel basis, and owns the
prospective headroom comparison against the R358 10/16 baseline.  It does not
load repository artifacts, execute a simulator, fit from holdout data, or
write a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from andes_rl_kundur.control.common_channel_qp import (
    build_four_channel_control_response_map,
    solve_common_channel_joint_endpoint_qp,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits

R358_BASELINE_FEASIBLE_COUNT = 10
DEVELOPMENT_CASE_COUNT = 16


def build_development_cases() -> list[dict[str, Any]]:
    """Rebuild the exact exposed R358 development bank."""

    from scripts.run_r358_physical_joint_endpoint_qp import build_development_cases as parent

    cases = parent()
    if len(cases) != DEVELOPMENT_CASE_COUNT:
        raise ValueError("R363 requires exactly sixteen development cases")
    return cases


def r358_status_partition() -> dict[str, list[str]]:
    """Return the frozen R358 optimal/primal-infeasible scenario partition."""

    from scripts.run_r358_physical_joint_endpoint_qp import r356_status_partition as parent

    return parent()


def solve_common_channel_bank(cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Solve every development case over the four-channel action basis."""

    rows: list[dict[str, Any]] = []
    limits = FeedbackLimits()
    for case in cases:
        outputs = np.asarray(case["base_outputs"], dtype=float)
        response = build_four_channel_control_response_map(
            case["model"],
            horizon=int(outputs.shape[0]),
        )
        result = solve_common_channel_joint_endpoint_qp(
            base_outputs=outputs,
            base_node_commands=case["base_node_commands"],
            previous_node_command=case["previous_node_command"],
            initial_soc=case["initial_soc"],
            response_map=response,
            minimum_improvement_fraction=0.02,
            limits=limits,
        )
        rows.append(
            {
                "scenario_id": str(case["scenario_id"]),
                "point": str(case["point"]),
                "channel": str(case["channel"]),
                "sign": str(case["sign"]),
                **result,
            }
        )
    return rows


def classify_common_channel_gate(
    *,
    cases: Sequence[Mapping[str, Any]],
    rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify the R363 headroom comparison against the R358 baseline."""

    if len(cases) != DEVELOPMENT_CASE_COUNT or len(rows) != DEVELOPMENT_CASE_COUNT:
        raise ValueError("R363 requires exactly sixteen solved development cases")
    by_id = {str(row["scenario_id"]): row for row in rows}
    if set(by_id) != {str(case["scenario_id"]) for case in cases}:
        raise ValueError("R363 solved rows must cover every development case")
    accepted = [str(row["scenario_id"]) for row in rows if row.get("accepted") is True]
    target_feasible = [
        str(row["scenario_id"]) for row in rows if row.get("target_feasible") is True
    ]
    integrity = {
        "complete_inventory": len(by_id) == DEVELOPMENT_CASE_COUNT,
        "all_solved": all(row.get("status") == "optimal" for row in rows),
        "all_certified": all(
            row.get("optimizer_valid") is True or row.get("target_feasible") is not None
            for row in rows
        ),
    }
    if not all(integrity.values()):
        return {
            "classification": "ANALYSIS-INVALID",
            "failed_integrity_checks": [
                str(name) for name, passed in integrity.items() if passed is not True
            ],
            "accepted_scenario_ids": accepted,
            "target_feasible_scenario_ids": target_feasible,
            "feasible_count": len(accepted),
            "r358_baseline_feasible_count": R358_BASELINE_FEASIBLE_COUNT,
            "training_authorized": False,
            "simulation_authorized": False,
            "eval_authorized": False,
        }
    partition = r358_status_partition()
    previously_infeasible = set(partition["primal_infeasible"])
    newly_feasible = sorted(set(accepted) & previously_infeasible)
    feasible_count = len(accepted)
    expanded = feasible_count > R358_BASELINE_FEASIBLE_COUNT or bool(newly_feasible)
    classification = (
        "COMMON-CHANNEL-HEADROOM-EXPANDED"
        if expanded
        else "COMMON-CHANNEL-HEADROOM-UNCHANGED"
    )
    return {
        "classification": classification,
        "failed_integrity_checks": [],
        "accepted_scenario_ids": sorted(accepted),
        "target_feasible_scenario_ids": sorted(target_feasible),
        "feasible_count": feasible_count,
        "r358_baseline_feasible_count": R358_BASELINE_FEASIBLE_COUNT,
        "previously_infeasible_scenario_ids": sorted(previously_infeasible),
        "newly_feasible_scenario_ids": newly_feasible,
        "headroom_expanded": expanded,
        "successor_question_authorized": expanded,
        "training_authorized": False,
        "simulation_authorized": False,
        "eval_authorized": False,
    }
