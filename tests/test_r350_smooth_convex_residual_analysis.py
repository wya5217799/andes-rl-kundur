"""Contract tests for the R350 sealed execution adapter."""

from __future__ import annotations

from scripts import run_r350_smooth_convex_residual as r350


def test_contract_freezes_three_starts_and_high_parallel_budget() -> None:
    contract = r350.build_contract()

    assert contract["round"] == "R350"
    assert contract["numerical_repair"]["starts"] == [
        "feasibility",
        "zero",
        "r348",
    ]
    assert contract["execution"]["worker_processes"] == 16
    assert contract["execution"]["host_process_budget"] == 32
    assert contract["execution"]["windows_python_processes"] == 17
    assert contract["execution"]["native_threads_per_process"] == 1
    assert contract["authorizations"] == {
        "simulation_authorized": False,
        "training_authorized": False,
        "distributed_runtime_authorized": False,
        "eval_authorized": False,
        "reward_design_authorized": False,
    }


def test_contract_keeps_training_blocked_for_every_classification() -> None:
    contract = r350.build_contract()

    assert contract["decision"]["maximum_positive_classification"] == (
        "RESIDUAL-PROBE-ELIGIBLE"
    )
    assert contract["decision"]["training_authorized"] is False
