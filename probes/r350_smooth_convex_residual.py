"""Fixed three-start smooth convex residual solve for R350.

This create-only probe recomputes the exposed R348 candidate, runs the two
additional prospectively registered initializations, and selects only among
independently certified physical-feasible results.  It owns no scientific
classification and executes no simulator, training, reward, or policy.
"""

from __future__ import annotations

from dataclasses import dataclass

from probes.r348_fully_normalized_residual import (
    solve_fully_normalized_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.convex_residual_solver import (
    ConvexResidualSolveResult,
    solve_convex_minimum_norm_edge_residual,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits


@dataclass(frozen=True)
class ResidualStartResult:
    """One named, prospectively registered numerical start."""

    name: str
    result: ConvexResidualSolveResult


@dataclass(frozen=True)
class ThreeStartResidualResult:
    """All fixed starts plus the deterministic certified selection."""

    starts: tuple[ResidualStartResult, ...]
    selected: ConvexResidualSolveResult | None
    selected_start: str | None
    certified_start_count: int
    r348_optimizer_valid: bool


def solve_three_start_edge_residual(
    *,
    base_outputs: object,
    base_node_commands: object,
    previous_node_command: object,
    initial_soc: object,
    response_map: object,
    limits: FeedbackLimits = FeedbackLimits(),
    minimum_improvement_fraction: float,
    maximum_iterations: int,
    function_tolerance: float,
    feasibility_tolerance: float,
) -> ThreeStartResidualResult:
    """Run the frozen feasibility, zero, and recomputed-R348 starts once."""

    inputs = {
        "base_outputs": base_outputs,
        "base_node_commands": base_node_commands,
        "previous_node_command": previous_node_command,
        "initial_soc": initial_soc,
        "response_map": response_map,
        "limits": limits,
        "minimum_improvement_fraction": minimum_improvement_fraction,
        "maximum_iterations": maximum_iterations,
        "function_tolerance": function_tolerance,
        "feasibility_tolerance": feasibility_tolerance,
    }
    r348 = solve_fully_normalized_minimum_norm_edge_residual(**inputs)
    starts = (
        ResidualStartResult(
            name="feasibility",
            result=solve_convex_minimum_norm_edge_residual(**inputs),
        ),
        ResidualStartResult(
            name="zero",
            result=solve_convex_minimum_norm_edge_residual(
                **inputs,
                use_feasibility_start=False,
            ),
        ),
        ResidualStartResult(
            name="r348",
            result=solve_convex_minimum_norm_edge_residual(
                **inputs,
                initial_edge_actions=r348.edge_actions,
                use_feasibility_start=False,
            ),
        ),
    )
    certified = [
        (index, start)
        for index, start in enumerate(starts)
        if start.result.feasible
    ]
    if certified:
        _index, chosen = min(
            certified,
            key=lambda item: (item[1].result.objective_value, item[0]),
        )
        selected = chosen.result
        selected_start = chosen.name
    else:
        selected = None
        selected_start = None
    return ThreeStartResidualResult(
        starts=starts,
        selected=selected,
        selected_start=selected_start,
        certified_start_count=len(certified),
        r348_optimizer_valid=bool(r348.optimizer_valid),
    )
