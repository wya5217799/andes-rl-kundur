"""Execution-boundary tests for the create-only R356 analysis."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts import run_r356_joint_endpoint_feasibility as runner


def test_contract_freezes_relaxed_development_only_no_training_gate() -> None:
    contract = runner.build_contract()

    assert contract["round"] == "R356"
    assert contract["target"]["minimum_improvement_fraction"] == 0.02
    assert contract["relaxation"]["physical_constraints_included"] is False
    assert contract["inventory"]["development_cases"] == 16
    assert contract["inventory"]["holdout_cases_read"] == 0
    assert contract["authorizations"]["training_authorized"] is False
    assert contract["authorizations"]["simulation_authorized"] is False


def test_source_and_parent_closure_include_only_authorized_inputs() -> None:
    sources = runner.source_paths(include_rehearsal=False)
    parents = runner.parent_paths()

    assert sources["adapter"] == Path(runner.__file__).resolve()
    assert sources["probe"].name == "r356_joint_endpoint_feasibility.py"
    assert sources["probe_tests"].name == "test_r356_joint_endpoint_feasibility.py"
    assert "r355_analysis" in parents
    assert "r341_candidate_models" in parents
    assert "r352_development_execution" in parents
    assert not any("holdout" in name or "formal_execution" in name for name in parents)


def test_cli_has_no_alternate_formal_output_path() -> None:
    parser = runner.build_parser()

    args = parser.parse_args(
        ["analyse", "--expected-seal-sha256", "0" * 64]
    )
    assert args.command == "analyse"
    assert not hasattr(args, "out")
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "analyse",
                "--expected-seal-sha256",
                "0" * 64,
                "--out",
                "alternate",
            ]
        )


def test_synthetic_solver_smoke_accepts_both_required_statuses() -> None:
    smoke = runner.synthetic_solver_smoke()

    assert smoke["infeasible"]["status"] == "primal infeasible"
    assert smoke["infeasible"]["accepted"] is True
    assert smoke["feasible"]["status"] == "optimal"
    assert smoke["feasible"]["accepted"] is True


def test_development_case_identity_matches_frozen_r355_analysis() -> None:
    cases = runner.build_development_cases()
    frozen = runner.read_json(runner.R355_ANALYSIS)["development_case_identity"]

    assert runner.case_identity(cases) == frozen
    assert len(cases) == 16
