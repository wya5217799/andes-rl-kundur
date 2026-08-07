"""Regression tests for the smooth convex residual-headroom solver."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.control.convex_residual_solver import (
    solve_convex_minimum_norm_edge_residual,
)
from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits


def _small_scale_long_horizon_inputs() -> dict[str, object]:
    """Return a public synthetic case that stalls the legacy nonsmooth solve."""

    generator = np.random.default_rng(3)
    steps = 5
    base_outputs = generator.normal(0.0, 1.5e-5, size=(steps, 4))
    base_outputs[:, 0] += (
        generator.choice([-1.0, 1.0], size=steps) * 4.0e-6
    )
    response_map = np.zeros((4 * steps, 3 * steps))
    impulse_blocks = [generator.normal(0.0, 0.012, size=(4, 3))]
    for lag in range(1, steps):
        impulse_blocks.append(
            (0.55**lag) * generator.normal(0.0, 0.012, size=(4, 3))
        )
    for output_step in range(steps):
        for action_step in range(output_step + 1):
            response_map[
                4 * output_step : 4 * (output_step + 1),
                3 * action_step : 3 * (action_step + 1),
            ] = impulse_blocks[output_step - action_step]
    return {
        "base_outputs": base_outputs,
        "base_node_commands": np.zeros((steps, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "response_map": response_map,
        "limits": FeedbackLimits(),
        "minimum_improvement_fraction": 0.02,
        "maximum_iterations": 20_000,
        "function_tolerance": 1.0e-9,
        "feasibility_tolerance": 1.0e-8,
    }


def test_solver_certifies_small_scale_long_horizon_minimum() -> None:
    result = solve_convex_minimum_norm_edge_residual(
        **_small_scale_long_horizon_inputs()
    )

    assert result.feasible, result.message
    assert result.target_feasible
    assert result.certificate.valid, result.certificate.reason
    assert result.maximum_constraint_residual <= 1.0e-8
    assert result.edge_actions.shape == (5, 3)

