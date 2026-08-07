"""Execution-boundary tests for the create-only R357 analysis."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_r357_physical_joint_endpoint_feasibility as runner


def test_contract_freezes_physical_development_only_no_training_gate() -> None:
    contract = runner.build_contract()

    assert contract["round"] == "R357"
    assert contract["question"] == "Q-0095"
    assert contract["target"]["minimum_improvement_fraction"] == 0.02
    assert contract["physical_constraints"]["node_power_included"] is True
    assert contract["physical_constraints"]["node_ramp_included"] is True
    assert contract["physical_constraints"]["soc_redundancy_required"] is True
    assert contract["inventory"]["development_cases"] == 16
    assert contract["inventory"]["holdout_cases_read"] == 0
    assert contract["authorizations"]["training_authorized"] is False
    assert contract["authorizations"]["simulation_authorized"] is False


def test_source_and_parent_closure_bind_r356_without_holdout() -> None:
    sources = runner.source_paths(include_rehearsal=False)
    parents = runner.parent_paths()

    assert sources["adapter"] == Path(runner.__file__).resolve()
    assert sources["probe"].name == "r357_physical_joint_endpoint_feasibility.py"
    assert "r356_analysis" in parents
    assert "r356_manifest" in parents
    assert not any("holdout" in name or "formal_execution" in name for name in parents)


def test_cli_has_no_alternate_formal_output_path() -> None:
    parser = runner.build_parser()
    args = parser.parse_args(["analyse", "--expected-seal-sha256", "0" * 64])

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


def test_synthetic_smoke_covers_endpoint_and_physical_infeasibility() -> None:
    smoke = runner.synthetic_solver_smoke()

    assert smoke["endpoint_infeasible"]["status"] == "primal infeasible"
    assert smoke["endpoint_infeasible"]["accepted"] is True
    assert smoke["physical_infeasible"]["status"] == "primal infeasible"
    assert smoke["physical_infeasible"]["accepted"] is True
    assert smoke["feasible"]["status"] == "optimal"
    assert smoke["feasible"]["accepted"] is True


def test_development_identity_and_r356_partition_are_frozen() -> None:
    cases = runner.build_development_cases()
    partition = runner.r356_status_partition()

    assert len(cases) == 16
    assert len(partition["primal_infeasible"]) == 6
    assert len(partition["optimal"]) == 10
    assert set(partition["primal_infeasible"]) | set(partition["optimal"]) == {
        str(case["scenario_id"]) for case in cases
    }

