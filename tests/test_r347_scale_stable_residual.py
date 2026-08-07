"""Contract tests for the scale-stable R347 residual analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import scripts.run_r345_residual_headroom as r345
import scripts.run_r347_scale_stable_residual as adapter
from probes.r345_residual_headroom import build_control_response_map
from probes.r347_scale_stable_residual import (
    solve_scale_stable_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputRealization,
)


def _model(*, reachable: bool) -> SeparateInputRealization:
    direct = np.zeros((4, 4))
    if reachable:
        direct[0, 1:] = 0.25
        direct[1:, 1:] = np.eye(3)
    return SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )


def _solve(*, scale: float, reachable: bool):
    horizon = 5
    model = _model(reachable=reachable)
    outputs = scale * np.tile(
        np.asarray([0.02, 0.03, -0.02, 0.01]),
        (horizon, 1),
    )
    return solve_scale_stable_minimum_norm_edge_residual(
        base_outputs=outputs,
        base_node_commands=np.zeros((horizon, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=build_control_response_map(model, horizon=horizon),
        limits=FeedbackLimits(),
        minimum_improvement_fraction=0.02,
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )


def test_relative_slack_is_valid_across_four_orders_of_output_scale() -> None:
    ordinary = _solve(scale=1.0, reachable=True)
    small = _solve(scale=1.0e-4, reachable=True)

    for result in (ordinary, small):
        assert result.optimizer_valid, result.message
        assert result.target_feasible, result.message
        assert result.feasible, result.message
        assert result.maximum_target_shortfall <= 1.0e-8


def test_relative_slack_preserves_valid_unreachable_target_classification() -> None:
    result = _solve(scale=1.0e-4, reachable=False)

    assert result.optimizer_valid, result.message
    assert not result.target_feasible
    assert not result.feasible
    assert result.maximum_target_shortfall > 0.0


def test_contract_keeps_r345_science_and_changes_only_slack_coordinates() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R347"
    assert contract["question"] == "Q-0091"
    assert contract["parent_scientific_contract"] == r345.build_contract()
    assert contract["numerical_repair"] == {
        "absolute_slack_replaced": True,
        "relative_slack_initial": [0.02, 0.02],
        "relative_slack_objective": "sum-of-squared-relative-shortfalls",
        "scientific_feasible_set_changed": False,
    }
    assert contract["execution"]["worker_processes"] == 16
    assert contract["execution"]["native_threads_per_process"] == 1
    assert not any(contract["authorizations"].values())


def test_oracle_diagnostic_projection_omits_outcomes_and_actions() -> None:
    case = {
        "scenario_id": "case-1",
        "point": "FV0",
        "channel": "PQ_0",
        "sign": "positive",
    }
    worker = {
        "scenario_id": "case-1",
        "worker_pid": 321,
        "elapsed_seconds": 0.25,
        "optimizer_valid": True,
        "target_feasible": False,
        "feasible": False,
        "message": "valid target infeasibility",
        "solver_iterations": 4,
        "maximum_constraint_residual": 0.0,
        "maximum_target_shortfall": 1.0e-6,
        "objective_value": 0.01,
        "nominal_endpoints": {"forbidden": 1.0},
        "edge_actions": [[1.0, 2.0, 3.0]],
    }

    row = adapter.project_oracle_diagnostic(case, worker)

    assert "nominal_endpoints" not in row
    assert "edge_actions" not in row
    assert row["optimizer_valid"] is True
    assert row["target_feasible"] is False
    assert row["maximum_target_shortfall"] == 1.0e-6


def test_prepare_is_create_only_and_binds_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seal = tmp_path / "analysis_seal.json"
    result_root = tmp_path / "result"
    plan = tmp_path / "plan.md"
    plan.write_text("state: active\nR347\nQ-0091\n", encoding="utf-8")
    sources = {"adapter": {"path": "adapter.py", "sha256": "a" * 64}}
    monkeypatch.setattr(adapter, "PLAN", plan)
    monkeypatch.setattr(adapter, "DEFAULT_OUT", result_root)
    monkeypatch.setattr(adapter, "_verify_frozen_inputs", lambda: None)
    monkeypatch.setattr(adapter, "_seal_sources", lambda: sources)

    digest = adapter.prepare(seal)
    payload, verified = adapter.load_seal(seal, digest)

    assert verified == digest
    assert payload["contract"] == adapter.build_contract()
    assert payload["sources"] == sources
    with pytest.raises(FileExistsError, match="seal already exists"):
        adapter.prepare(seal)


def test_parser_exposes_no_simulation_training_eval_or_reward_command() -> None:
    parser = adapter.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")

    assert set(subparsers.choices) == {"prepare", "analyse"}
    assert not {
        "simulate",
        "execute",
        "train",
        "eval",
        "reward",
        "distributed",
    } & set(subparsers.choices)
