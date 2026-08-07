"""Contract tests for the fixed R350 three-start residual solve."""

from __future__ import annotations

import numpy as np
from probes.r345_residual_headroom import build_control_response_map
from probes.r350_smooth_convex_residual import solve_three_start_edge_residual

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import SeparateInputRealization


def _worked_inputs() -> dict[str, object]:
    direct = np.zeros((4, 4))
    direct[:, 1] = np.asarray([-1.0, -1.0, 0.0, 0.0])
    model = SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )
    return {
        "base_outputs": np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        "base_node_commands": np.zeros((1, 4)),
        "previous_node_command": np.zeros(4),
        "initial_soc": np.full(4, 0.5),
        "response_map": build_control_response_map(model, horizon=1),
        "limits": FeedbackLimits(),
        "minimum_improvement_fraction": 0.02,
        "maximum_iterations": 20_000,
        "function_tolerance": 1.0e-9,
        "feasibility_tolerance": 1.0e-8,
    }


def test_three_start_solver_selects_one_certified_minimum() -> None:
    result = solve_three_start_edge_residual(**_worked_inputs())

    assert result.selected is not None
    assert result.selected.feasible
    assert result.selected.certificate.valid
    assert tuple(start.name for start in result.starts) == (
        "feasibility",
        "zero",
        "r348",
    )
    assert result.selected_start in {start.name for start in result.starts}
    assert result.certified_start_count >= 1
    np.testing.assert_allclose(
        result.selected.edge_actions,
        np.asarray([[0.02, 0.0, 0.0]]),
        rtol=0.0,
        atol=1.0e-6,
    )
