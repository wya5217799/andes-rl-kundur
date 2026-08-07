"""Regression tests for numerically stable physical endpoint feasibility."""

from __future__ import annotations

import numpy as np
import probes.physical_joint_endpoint_qp as qp
import pytest
from probes.physical_joint_endpoint_qp import solve_physical_joint_endpoint_qp
from scripts import run_r357_physical_joint_endpoint_feasibility as r357

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.residual_headroom import build_control_response_map


def test_minimized_r357_domain_error_returns_verified_optimum() -> None:
    """The four-step prefix that crashed CVXOPT SOCP must return normally."""

    case = r357.build_development_cases()[4]
    steps = 4
    outputs = np.asarray(case["base_outputs"], dtype=float)[:steps]
    response = build_control_response_map(case["model"], horizon=25)[: 4 * steps, : 3 * steps]

    result = solve_physical_joint_endpoint_qp(
        base_outputs=outputs,
        base_node_commands=np.asarray(case["base_node_commands"], dtype=float)[:steps],
        previous_node_command=case["previous_node_command"],
        initial_soc=case["initial_soc"],
        response_map=response,
        minimum_improvement_fraction=0.02,
        limits=FeedbackLimits(),
    )

    assert result["status"] == "optimal"
    assert result["accepted"] is True
    assert result["target_feasible"] is True
    assert result["differential_ratio"] <= 0.98 + 1.0e-8


def test_all_exposed_relaxed_candidates_return_verified_decisions() -> None:
    """Every R356 candidate must avoid an exception or ambiguous solver exit."""

    candidate_ids = set(r357.r356_status_partition()["optimal"])
    results = []
    for case in r357.build_development_cases():
        if case["scenario_id"] not in candidate_ids:
            continue
        outputs = np.asarray(case["base_outputs"], dtype=float)
        response = build_control_response_map(case["model"], horizon=int(outputs.shape[0]))
        results.append(
            solve_physical_joint_endpoint_qp(
                base_outputs=outputs,
                base_node_commands=case["base_node_commands"],
                previous_node_command=case["previous_node_command"],
                initial_soc=case["initial_soc"],
                response_map=response,
                minimum_improvement_fraction=0.02,
                limits=FeedbackLimits(),
            )
        )

    assert len(results) == 10
    assert all(result["status"] == "optimal" for result in results)
    assert all(result["accepted"] is True for result in results)
    assert all(result["target_feasible"] is True for result in results)


def test_dual_lower_bound_can_certify_target_infeasibility() -> None:
    """A fixed differential endpoint is rejected by a verified lower bound."""

    limits = FeedbackLimits()
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp

    result = solve_physical_joint_endpoint_qp(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=response,
        minimum_improvement_fraction=0.02,
        limits=limits,
    )

    assert result["status"] == "optimal"
    assert result["accepted"] is True
    assert result["target_feasible"] is False
    assert result["dual_lower_bound_ratio"] > 0.98 + 1.0e-8


def test_solver_exception_returns_invalid_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A numerical library exception must fail closed without escaping."""

    def fail_solver(*args, **kwargs):
        raise ValueError("domain error")

    monkeypatch.setattr(qp.solvers, "qp", fail_solver)
    limits = FeedbackLimits()
    response = np.zeros((4, 3))
    response[0, 0] = -1.0 / limits.node_ramp

    result = solve_physical_joint_endpoint_qp(
        base_outputs=np.asarray([[1.0, 1.0, 0.0, 0.0]]),
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=response,
        minimum_improvement_fraction=0.02,
        limits=limits,
    )

    assert result["status"] == "solver error"
    assert result["accepted"] is False
    assert result["target_feasible"] is None
    assert result["error_type"] == "ValueError"
