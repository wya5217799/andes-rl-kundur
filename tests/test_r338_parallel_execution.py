from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts import run_r293_formal as formal_core
from scripts import run_r338_parallel_execution as adapter


def test_contract_preserves_the_paper_comparison_and_changes_only_execution() -> None:
    contract = adapter.build_contract()

    assert contract["round"] == "R338"
    assert contract["question"] == "Q-0088"
    assert contract["title"] == (
        "Decoupling-Oriented Coordination of Paralleled VSGs With "
        "Multi-Agent Reinforcement Learning"
    )
    assert contract["title_changed"] is False
    assert contract["scientific_object_changed"] is False
    assert contract["execution"]["wsl_workers"] == 3
    assert contract["execution"]["native_threads_per_worker"] == 1
    assert contract["execution"]["new_formal_trajectories"] == 264
    assert contract["execution"]["reused_q0_trajectories"] == 24
    assert contract["execution"]["automatic_retry"] is False
    assert contract["upstreams"]["training"] == (
        "results/r337_prior_residual_training"
    )
    assert contract["upstreams"]["fresh_bank"] == "results/r337_fresh_bank"
    assert "results/r337_formal_evaluation" in contract["forbidden_inputs"]


def test_canary_is_small_fixed_and_not_a_performance_experiment() -> None:
    canary = adapter.build_canary_contract()

    assert canary["steps"] == 15
    assert canary["arms"] == [
        "classical_edge",
        "central_prior_s421",
        "distributed_prior_s421",
    ]
    assert canary["worker_count"] == 3
    assert canary["scenario_selection"] == "first_frozen_scenario"
    assert canary["performance_endpoints_inspected"] is False
    assert canary["automatic_formal_release"] is False


def test_formal_configuration_uses_new_outputs_and_only_preformal_r337_inputs() -> None:
    original_round = formal_core.ROUND_ID

    with adapter._configured_formal() as configured:
        assert configured.ROUND_ID == "R338"
        assert configured.QUESTION_ID == "Q-0088"
        assert configured.DEFAULT_OUT == adapter.FORMAL_OUT
        assert configured.FORMAL_BANK == adapter.R337_FRESH_OUT / "formal_bank.json"
        assert configured.TRAINING_SUMMARY == (
            adapter.R337_TRAINING_OUT / "training_matrix_summary.json"
        )
        assert configured._checkpoint_path("distributed_prior", 421) == (
            adapter.R337_TRAINING_OUT / "distributed_prior_s421" / "final.pt"
        )

    assert formal_core.ROUND_ID == original_round
    source_text = "\n".join(
        path.as_posix() for path in adapter._formal_source_paths().values()
    )
    assert "results/r337_prior_residual_training" in source_text
    assert "results/r337_fresh_bank" in source_text
    assert "results/r337_formal_evaluation" not in source_text
    assert "memory/rounds/R337/formal_seal.json" not in source_text
    assert "memory/rounds/R337/formal_failure.json" not in source_text


def test_prepare_freezes_a_new_264_trajectory_seal_without_old_formal_inputs(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "formal_seal.json"
    adapter.prepare(
        manifest,
        tmp_path / "formal_out",
        canary_out=tmp_path / "canary_out",
    )

    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["round"] == "R338"
    assert payload["question"] == "Q-0088"
    assert payload["execution"]["new_controller_trajectory_budget"] == 264
    assert payload["execution"]["reused_q0_trajectory_count"] == 24
    paths = {entry["path"] for entry in payload["sources"].values()}
    assert "results/r337_prior_residual_training/training_matrix_summary.json" in paths
    assert "results/r337_fresh_bank/formal_bank.json" in paths
    assert not any("r337_formal_evaluation" in path for path in paths)


def test_cli_exposes_separate_small_step_gates(tmp_path: Path) -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(adapter.__file__).resolve()), "--help"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    for command in ("prepare", "canary-worker", "verify-canary", "run", "analyse"):
        assert command in completed.stdout


def test_adapter_can_import_frozen_core_from_a_scratch_working_directory(
    tmp_path: Path,
) -> None:
    script = Path(adapter.__file__).resolve()
    code = (
        "import runpy; "
        f"ns = runpy.run_path({str(script)!r}); "
        "cm = ns['_configured_formal'](); "
        "formal = cm.__enter__(); "
        "print(formal.ROUND_ID); "
        "cm.__exit__(None, None, None)"
    )

    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "R338"
