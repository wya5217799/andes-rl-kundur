"""Contract tests for the fully normalized R348 residual analysis."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import scripts.run_r345_residual_headroom as r345
import scripts.run_r348_fully_normalized_residual as adapter
from probes.r345_residual_headroom import build_control_response_map, endpoint_values
from probes.r348_fully_normalized_residual import (
    solve_fully_normalized_minimum_norm_edge_residual,
)

from andes_rl_kundur.control.model_first_offline_feedback import FeedbackLimits
from andes_rl_kundur.control.model_first_separate_input import (
    SeparateInputRealization,
)


def _worked_model(*, output_scale: float, reachable: bool) -> SeparateInputRealization:
    direct = np.zeros((4, 4))
    if reachable:
        direct[:, 1] = output_scale * np.asarray([-1.0, -1.0, 0.0, 0.0])
    return SeparateInputRealization(
        state_matrix=np.zeros((4, 4)),
        control_input_matrix=np.zeros((4, 4)),
        disturbance_input_matrix=np.zeros((4, 4)),
        output_matrix=np.eye(4),
        control_feedthrough_matrix=direct,
        disturbance_feedthrough_matrix=np.zeros((4, 4)),
        retained_singular_values=np.ones(4),
    )


def _solve(*, output_scale: float, reachable: bool):
    model = _worked_model(output_scale=output_scale, reachable=reachable)
    base = output_scale * np.asarray([[1.0, 1.0, 0.0, 0.0]])
    return solve_fully_normalized_minimum_norm_edge_residual(
        base_outputs=base,
        base_node_commands=np.zeros((1, 4)),
        previous_node_command=np.zeros(4),
        initial_soc=np.full(4, 0.5),
        response_map=build_control_response_map(model, horizon=1),
        limits=FeedbackLimits(),
        minimum_improvement_fraction=0.02,
        maximum_iterations=20_000,
        function_tolerance=1.0e-9,
        feasibility_tolerance=1.0e-8,
    )


def test_fully_normalized_solution_matches_worked_minimum_across_output_scales() -> None:
    for output_scale in (1.0, 1.0e-4):
        result = _solve(output_scale=output_scale, reachable=True)

        assert result.optimizer_valid, result.message
        assert result.target_feasible, result.message
        assert result.feasible, result.message
        np.testing.assert_allclose(
            result.edge_actions,
            np.asarray([[0.02, 0.0, 0.0]]),
            rtol=0.0,
            atol=1.0e-6,
        )
        base_endpoints = endpoint_values(
            output_scale * np.asarray([[1.0, 1.0, 0.0, 0.0]]),
            sample_period_seconds=0.2,
        )
        candidate_endpoints = endpoint_values(
            result.counterfactual_outputs,
            sample_period_seconds=0.2,
        )
        assert candidate_endpoints["common_coordinate_iae"] <= (
            0.98 * base_endpoints["common_coordinate_iae"] + 1.0e-8
        )
        assert candidate_endpoints["differential_coordinate_energy"] <= (
            0.98 * base_endpoints["differential_coordinate_energy"] + 1.0e-8
        )
        assert result.maximum_constraint_residual <= 1.0e-8


def test_fully_normalized_relaxation_preserves_valid_unreachable_target() -> None:
    result = _solve(output_scale=1.0e-4, reachable=False)

    assert result.optimizer_valid, result.message
    assert not result.target_feasible
    assert not result.feasible
    assert result.maximum_target_shortfall > 0.0


def test_contract_keeps_parent_science_and_freezes_only_numerical_scaling() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R348"
    assert contract["question"] == "Q-0091"
    assert contract["parent_scientific_contract"] == r345.build_contract()
    assert contract["numerical_repair"] == {
        "relative_endpoint_slacks": True,
        "edge_variable_scale": "frozen-node-ramp",
        "endpoint_constraint_scale": "scenario-baseline-endpoint",
        "power_constraint_scale": "frozen-node-power",
        "ramp_constraint_scale": "frozen-node-ramp",
        "soc_constraint_scale": "frozen-soc-span",
        "scientific_feasible_set_changed": False,
        "minimum_norm_solution_changed": False,
    }
    assert contract["execution"]["worker_processes"] == 16
    assert contract["execution"]["native_threads_per_process"] == 1
    assert not any(contract["authorizations"].values())


def test_prepare_is_create_only_and_binds_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seal = tmp_path / "analysis_seal.json"
    result_root = tmp_path / "result"
    plan = tmp_path / "plan.md"
    plan.write_text("state: active\nR348\nQ-0091\n", encoding="utf-8")
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
