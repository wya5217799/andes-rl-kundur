"""Public contract tests for the R346 optimizer-invalidity diagnosis."""

from __future__ import annotations

from pathlib import Path

import pytest
import scripts.run_r346_r345_optimizer_diagnosis as adapter


def test_contract_freezes_sixteen_metadata_only_jobs_and_all_exclusions() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R346"
    assert contract["parent_round"] == "R345"
    assert contract["scenario_count"] == 16
    assert contract["execution"] == {
        "worker_processes": 16,
        "native_threads_per_process": 1,
        "create_only": True,
        "retry_authorized": False,
    }
    assert contract["diagnostic_only"] is True
    assert not any(contract["authorizations"].values())


def test_metadata_projection_omits_every_scientific_outcome_and_action() -> None:
    case = {
        "scenario_id": "case-1",
        "point": "HS0",
        "channel": "PQ_0",
        "sign": "positive",
    }
    worker = {
        "scenario_id": "case-1",
        "worker_pid": 123,
        "elapsed_seconds": 0.5,
        "optimizer_valid": False,
        "target_feasible": True,
        "feasible": False,
        "message": "minimum norm failed",
        "solver_iterations": 12,
        "maximum_constraint_residual": 1.0e-5,
        "maximum_target_shortfall": 0.0,
        "objective_value": 0.25,
        "base_endpoints": {"forbidden": 1.0},
        "nominal_endpoints": {"forbidden": 2.0},
        "edge_actions": [[1.0, 2.0, 3.0]],
        "counterfactual_soc": [[0.5] * 4],
    }

    actual = adapter.project_diagnostic_row(case, worker)

    assert actual == {
        "scenario_id": "case-1",
        "point": "HS0",
        "channel": "PQ_0",
        "sign": "positive",
        "worker_pid": 123,
        "elapsed_seconds": 0.5,
        "worker_exception": False,
        "optimizer_valid": False,
        "target_feasible": True,
        "feasible": False,
        "message": "minimum norm failed",
        "solver_iterations": 12,
        "maximum_constraint_residual": 1.0e-5,
        "maximum_target_shortfall": 0.0,
        "objective_value": 0.25,
    }


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (
            [{"worker_exception": True}],
            "WORKER-EXCEPTION",
        ),
        (
            [
                {
                    "worker_exception": False,
                    "optimizer_valid": False,
                    "target_feasible": False,
                }
            ],
            "RELAXATION-INVALID",
        ),
        (
            [
                {
                    "worker_exception": False,
                    "optimizer_valid": False,
                    "target_feasible": True,
                }
            ],
            "MINIMUM-NORM-INVALID",
        ),
        (
            [
                {
                    "worker_exception": False,
                    "optimizer_valid": True,
                    "target_feasible": True,
                }
            ],
            "NONREPRODUCIBLE-OPTIMIZER-INVALIDITY",
        ),
    ],
)
def test_classifier_localizes_only_the_numerical_stage(
    rows: list[dict[str, object]],
    expected: str,
) -> None:
    decision = adapter.classify_diagnostic_rows(rows)

    assert decision["classification"] == expected
    assert decision["scientific_result_authorized"] is False
    assert decision["question_disposition_authorized"] is False
    assert decision["residual_probe_authorized"] is False
    assert decision["training_authorized"] is False
    assert decision["distributed_runtime_authorized"] is False
    assert decision["eval_authorized"] is False


def test_prepare_is_create_only_and_binds_sources(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seal = tmp_path / "diagnostic_seal.json"
    result_root = tmp_path / "result"
    plan = tmp_path / "plan.md"
    plan.write_text("state: active\nR346\nQ-0091\n", encoding="utf-8")
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
    assert payload["result_root_absent_at_freeze"] is True
    with pytest.raises(FileExistsError, match="seal already exists"):
        adapter.prepare(seal)


def test_parser_exposes_only_prepare_and_diagnose() -> None:
    parser = adapter.build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")

    assert set(subparsers.choices) == {"prepare", "diagnose"}
    assert not {
        "analyse",
        "simulate",
        "execute",
        "train",
        "eval",
        "local-reconstruction",
    } & set(subparsers.choices)
