"""Execution-boundary tests for the create-only R358 recovery analysis."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from scripts import run_r358_physical_joint_endpoint_qp as runner


def test_contract_freezes_normalized_candidate_only_no_training_gate() -> None:
    contract = runner.build_contract()

    assert contract["round"] == "R358"
    assert contract["question"] == "Q-0095"
    assert contract["target"]["minimum_improvement_fraction"] == 0.02
    assert contract["inventory"]["development_cases"] == 16
    assert contract["inventory"]["inherited_infeasible_controls"] == 6
    assert contract["inventory"]["quadratic_candidates"] == 10
    assert contract["inventory"]["holdout_cases_read"] == 0
    assert contract["solver"]["name"] == "cvxopt-qp"
    assert contract["authorizations"]["training_authorized"] is False
    assert contract["authorizations"]["simulation_authorized"] is False


def test_source_and_parent_closure_bind_r356_and_invalid_r357() -> None:
    sources = runner.source_paths(include_rehearsal=False)
    parents = runner.parent_paths()

    assert sources["adapter"] == Path(runner.__file__).resolve()
    assert sources["probe"].name == "physical_joint_endpoint_qp.py"
    assert sources["probe_tests"].name == "test_physical_joint_endpoint_qp.py"
    assert "r356_analysis" in parents
    assert "r357_failure" in parents
    assert "r357_attempt" in parents
    assert not any("holdout" in name for name in parents)


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


def test_script_entry_defines_cli_before_dispatch() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(runner.__file__).resolve()), "--help"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "rehearsal" in completed.stdout
    assert "prepare" in completed.stdout
    assert "analyse" in completed.stdout


def test_rehearsal_checks_cover_partition_and_numerical_regression() -> None:
    cases = runner.verify_frozen_inputs()
    partition = runner.r356_status_partition()
    smoke = runner.synthetic_solver_smoke()
    regression = runner.minimized_r357_regression()

    assert len(cases) == 16
    assert len(partition["primal_infeasible"]) == 6
    assert len(partition["optimal"]) == 10
    assert smoke["feasible"]["accepted"] is True
    assert smoke["feasible"]["target_feasible"] is True
    assert smoke["target_infeasible"]["accepted"] is True
    assert smoke["target_infeasible"]["target_feasible"] is False
    assert regression["status"] == "optimal"
    assert regression["accepted"] is True
    assert regression["target_feasible"] is True


def test_rehearsal_and_prepare_are_create_only_and_bind_closures(tmp_path) -> None:
    rehearsal_path = tmp_path / "rehearsal.json"
    seal_path = tmp_path / "seal.json"
    formal_out = tmp_path / "formal"

    rehearsal_digest = runner.rehearsal(rehearsal_path, out_dir=formal_out)
    rehearsal = runner.predecessor.read_json(rehearsal_path)

    assert len(rehearsal_digest) == 64
    assert rehearsal["complete_candidate_bank_solved"] is False
    assert rehearsal["holdout_cases_read"] == 0
    assert rehearsal["formal_output_absent"] is True
    assert not formal_out.exists()

    seal_digest = runner.prepare(
        seal_path,
        rehearsal_path=rehearsal_path,
        out_dir=formal_out,
    )
    seal = runner.predecessor.read_json(seal_path)

    assert len(seal_digest) == 64
    assert seal["contract"] == runner.build_contract()
    assert seal["retry_authorized"] is False
    assert seal["result_root_absent_at_freeze"] is True
    assert not formal_out.exists()
    with pytest.raises(FileExistsError):
        runner.rehearsal(rehearsal_path, out_dir=formal_out)


def test_candidate_bank_classification_requires_ten_accepted_decisions() -> None:
    feasible_rows = [
        {"status": "optimal", "accepted": True, "target_feasible": True} for _ in range(10)
    ]
    infeasible_rows = [
        {"status": "optimal", "accepted": True, "target_feasible": False} for _ in range(10)
    ]

    assert (
        runner.classify_candidate_bank(feasible_rows)["classification"] == "PHYSICAL-HEADROOM-FOUND"
    )
    assert (
        runner.classify_candidate_bank(infeasible_rows)["classification"] == "NO-PHYSICAL-HEADROOM"
    )
    assert (
        runner.classify_candidate_bank(feasible_rows[:-1])["classification"] == "ANALYSIS-INVALID"
    )
    feasible_rows[0]["accepted"] = False
    assert runner.classify_candidate_bank(feasible_rows)["classification"] == "ANALYSIS-INVALID"
