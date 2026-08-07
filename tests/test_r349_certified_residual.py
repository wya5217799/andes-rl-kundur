"""Contract tests for the R349 independently certified residual solver."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from probes.r345_residual_headroom import build_control_response_map
from probes.r348_fully_normalized_residual import (
    solve_fully_normalized_minimum_norm_edge_residual,
)
from probes.r349_certified_residual import (
    solve_certified_fully_normalized_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputRealization,
)


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


def test_certified_solver_accepts_analytic_minimum() -> None:
    result = solve_certified_fully_normalized_minimum_norm_edge_residual(**_worked_inputs())

    assert result.solution.optimizer_valid, result.solution.message
    assert result.certificate is not None
    assert result.certificate.valid, result.certificate.reason
    np.testing.assert_allclose(
        result.solution.edge_actions,
        np.asarray([[0.02, 0.0, 0.0]]),
        rtol=0.0,
        atol=1.0e-6,
    )


def test_certificate_can_accept_exact_candidate_despite_false_solver_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import probes.r349_certified_residual as probe

    inputs = _worked_inputs()
    base = solve_fully_normalized_minimum_norm_edge_residual(**inputs)
    monkeypatch.setattr(
        probe,
        "solve_fully_normalized_minimum_norm_edge_residual",
        lambda **_kwargs: replace(
            base,
            feasible=False,
            optimizer_valid=False,
            message="synthetic false solver status",
        ),
    )

    result = solve_certified_fully_normalized_minimum_norm_edge_residual(**inputs)

    assert not result.base_optimizer_valid
    assert result.solution.optimizer_valid, result.solution.message
    assert result.certificate is not None
    assert result.certificate.valid


def test_certificate_rejects_feasible_nonminimum_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import probes.r349_certified_residual as probe

    inputs = _worked_inputs()
    base = solve_fully_normalized_minimum_norm_edge_residual(**inputs)
    monkeypatch.setattr(
        probe,
        "solve_fully_normalized_minimum_norm_edge_residual",
        lambda **_kwargs: replace(
            base,
            edge_actions=np.asarray([[0.03, 0.0, 0.0]]),
            feasible=True,
            optimizer_valid=True,
            message="synthetic feasible nonminimum",
        ),
    )

    result = solve_certified_fully_normalized_minimum_norm_edge_residual(**inputs)

    assert result.base_optimizer_valid
    assert not result.solution.optimizer_valid
    assert result.certificate is not None
    assert not result.certificate.valid
    assert result.certificate.reason == "stationarity-failed"
