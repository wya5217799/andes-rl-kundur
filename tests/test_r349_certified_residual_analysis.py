"""Contract tests for the sealed R349 analysis adapter."""

from __future__ import annotations

from pathlib import Path

import pytest
import scripts.run_r348_fully_normalized_residual as r348
import scripts.run_r349_certified_residual_analysis as adapter


def test_contract_preserves_r348_and_freezes_only_independent_acceptance() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R349"
    assert contract["question"] == "Q-0091"
    assert contract["parent_numerical_contract"] == r348.build_contract()
    assert contract["acceptance_certificate"] == {
        "objective": "minimum-dimensionless-edge-two-norm-squared",
        "constraint_convention": "dimensionless-g-greater-than-or-equal-to-zero",
        "feasibility_tolerance_original_units": 1.0e-8,
        "active_and_optimality_tolerance": 1.0e-4,
        "jacobian": "central-cbrt-machine-epsilon-relative-step",
        "multipliers": "nonnegative-least-squares",
        "requires_stationarity": True,
        "requires_complementarity": True,
        "upper_soc_guard": "dimensionless-slack-strictly-greater-than-1e-4",
        "candidate_changed": False,
        "scientific_contract_changed": False,
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
    plan.write_text("state: active\nR349\nQ-0091\n", encoding="utf-8")
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
