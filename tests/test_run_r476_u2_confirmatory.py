from __future__ import annotations

import inspect
from pathlib import Path

import numpy as np
import pytest
import scripts.run_r476_u2_confirmatory as R476


def test_successor_keeps_exact_all_fresh_scientific_cell_set() -> None:
    assert len(R476.RETRAIN_CELLS) == 48
    assert R476.REUSE_CELLS == ()
    assert set(R476.RETRAIN_ARMS) == {
        f"{base}_{reward}"
        for base in ("an_cn", "an_cp", "ap_cn", "ap_cp")
        for reward in ("r0", "r1")
    }
    assert R476.TRAIN_SHARD_IDS == tuple(
        f"train|{arm}|{seed}"
        for arm, seed in R476.RETRAIN_CELLS
    )
    assert len(R476.EVAL_SHARD_IDS) == 16


def test_contract_changes_only_successor_identity_and_governance() -> None:
    contract = R476.build_contract()
    assert contract["round"] == "R476"
    assert "r475" not in contract
    assert contract["r476"]["successor_of"] == "R475"
    assert "row permutation" in contract["r476"]["p_source_semantics"]
    assert contract["r476"]["retrain_cells"] == list(R476.TRAIN_SHARD_IDS)


def test_source_rows_delegates_frozen_row_permutation() -> None:
    joint = np.arange(28, dtype=np.float32).reshape(4, 7)
    rows = R476.source_rows(joint, "P")
    assert np.array_equal(rows[:, :3], joint[:, :3])
    for index in range(4):
        assert np.array_equal(rows[index, 3:7], joint[(index + 1) % 4, 3:7])


def test_load_seal_calls_r476_full_verifier_not_inherited_core(monkeypatch) -> None:
    observed = {}

    def fake_verify(**kwargs):
        observed.update(kwargs)
        return {"round": "R476"}

    monkeypatch.setattr(R476, "verify_formal_seal", fake_verify)
    assert R476.load_seal() == {"round": "R476"}
    assert observed["seal_path"] == R476.SEAL
    assert observed["round_id"] == "R476"
    assert observed["expected_shards"] == {
        "train": R476.TRAIN_SHARD_IDS,
        "eval": R476.EVAL_SHARD_IDS,
    }
    assert R476.base.core.load_seal is R476.load_seal


def test_rehearsal_replaces_literal_terminal_table_with_executable_truth(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        R476,
        "_r475_rehearsal",
        lambda: {"passed": True, "terminal_truth_table": {"literal": True}},
    )
    payload = R476.rehearsal()
    assert payload["passed"] is True
    assert payload["terminal_truth_table"] == {
        "normal_nonterminal_accepted": True,
        "normal_horizon_done_accepted": True,
        "premature_done_rejected": True,
        "tds_failure_rejected": True,
    }


def test_runner_is_adapter_not_a_second_training_implementation() -> None:
    source = inspect.getsource(R476)
    assert "def train_arm_seed" not in source
    assert "def evaluate_arm_stage" not in source
    assert "def routing_check" not in source
    assert "validate_review_coverage" in source
    assert "classify_confirmatory" in source


def test_r476_paths_do_not_reuse_r475_output() -> None:
    assert "r476" in R476.OUT.as_posix()
    assert "r475" not in R476.OUT.as_posix()
    assert R476.ROUND_ID == "R476"
    assert R476.PLAN == Path(R476.ROOT, "memory/rounds/R476/plan.md")


def test_artifact_budget_blocks_oversized_result_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(R476, "OUT", tmp_path)
    (tmp_path / "payload.bin").write_bytes(b"12345")
    assert R476.artifact_budget_check(max_bytes=5)["total_bytes"] == 5
    with pytest.raises(RuntimeError, match="artifact budget exceeded"):
        R476.artifact_budget_check(max_bytes=4)
