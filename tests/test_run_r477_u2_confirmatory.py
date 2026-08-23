from __future__ import annotations

import inspect
import os
from pathlib import Path

import numpy as np
import pytest
import scripts.run_r477_u2_confirmatory as R477


def test_successor_splits_16_reused_and_32_fresh_cells() -> None:
    assert len(R477.REUSED_CELLS) == 16
    assert len(R477.RETRAIN_CELLS) == 32
    assert set(R477.REUSED_CELLS).isdisjoint(R477.RETRAIN_CELLS)
    assert R477.REUSED_CELLS == R477._cells(R477.base.TRAIN_WAVE_IDS[0])
    assert R477.RETRAIN_CELLS == R477._cells(
        R477.base.TRAIN_WAVE_IDS[1] + R477.base.TRAIN_WAVE_IDS[2]
    )
    assert len(R477.TRAIN_SHARD_IDS) == 32
    assert len(R477.TRAIN_WAVE_IDS) == 2
    assert [len(wave) for wave in R477.TRAIN_WAVE_IDS] == [16, 16]
    assert len(R477.EVAL_SHARD_IDS) == 16
    assert R477.REUSE_ARMS == ()


def test_contract_declares_reuse_and_keeps_science() -> None:
    contract = R477.build_contract()
    assert contract["round"] == "R477"
    assert "r476" not in contract and "r470" not in contract
    inherited = contract["r477"]
    assert inherited["successor_of"] == "R476"
    assert inherited["reuse_source_round"] == "R476"
    assert "row permutation" in inherited["p_source_semantics"]
    assert inherited["retrain_cells"] == list(R477.TRAIN_SHARD_IDS)
    assert inherited["reused_cells"] == [
        f"train|{arm}|{seed}" for arm, seed in R477.REUSED_CELLS
    ]


def test_load_seal_expects_two_waves_and_eval(monkeypatch) -> None:
    observed = {}

    def fake_verify(**kwargs):
        observed.update(kwargs)
        return {"round": "R477"}

    monkeypatch.setattr(R477, "verify_formal_seal", fake_verify)
    assert R477.load_seal() == {"round": "R477"}
    assert observed["seal_path"] == R477.SEAL
    assert observed["round_id"] == "R477"
    assert observed["expected_shards"] == {
        "train": R477.TRAIN_SHARD_IDS,
        "train_wave_1": R477.TRAIN_WAVE_IDS[0],
        "train_wave_2": R477.TRAIN_WAVE_IDS[1],
        "eval": R477.EVAL_SHARD_IDS,
    }
    assert R477.base.base.core.load_seal is R477.load_seal


def test_runner_is_adapter_not_a_second_training_implementation() -> None:
    source = inspect.getsource(R477)
    assert "def routing_check" not in source
    assert "paired_log_effects" not in source
    assert "def _r476_train_arm_seed" not in source
    assert "_r476_train_arm_seed = base.train_arm_seed" in source
    assert "import_r476_training_shards" in source


def _import_manifest(valid: bool = True, factors_ok: bool = True, round_id: str = "R476") -> dict:
    arm, seed = R477.REUSED_CELLS[0]
    return {
        "round": round_id,
        "valid": valid,
        "interaction_steps": 43_200,
        "arm_id": arm,
        "training_seed": seed,
        "factors": R477.base.base.core.arm_factors(arm) if factors_ok else {"x": 1},
        "reward_function_sha256": "reward-sha",
        "base_state_sha256": "base-sha",
    }


def _setup_import_trees(
    monkeypatch,
    tmp_path: Path,
    manifest: dict,
    donor: dict | None = None,
    keep_factors: bool = False,
) -> tuple[Path, Path]:
    """Build R476 source and R477 target trees under tmp_path and route
    hashed reads so the real hardlink/stat path executes."""
    r476_out = tmp_path / "r476"
    out = tmp_path / "r477"
    monkeypatch.setattr(R477, "R476_OUT", r476_out)
    monkeypatch.setattr(R477, "OUT", out)
    core = R477.base.base.core
    for arm, seed in R477.REUSED_CELLS:
        source_dir = r476_out / "train" / arm / f"seed{seed}"
        source_dir.mkdir(parents=True, exist_ok=True)
        for name in ("manifest.json", "half.pt", "final.pt", "full_curves.npz"):
            (source_dir / name).write_bytes(b"x")
            (source_dir / f"{name}.sha256").write_bytes(b"x")
    for seed in {seed for _, seed in R477.REUSED_CELLS}:
        donor_dir = out / "donors" / f"seed{seed}"
        donor_dir.mkdir(parents=True, exist_ok=True)
        (donor_dir / "manifest.json").write_bytes(b"{}")
        (donor_dir / "manifest.json.sha256").write_bytes(b"x")
        (donor_dir / "base_state.pt").write_bytes(b"base")
    def fake_read(path: Path) -> dict:
        if "train" in str(path):
            parts = Path(path).parts
            arm = parts[parts.index("train") + 1]
            seed = int(next(p[4:] for p in parts if p.startswith("seed")))
            factors = (
                manifest["factors"]
                if keep_factors
                else R477.base.base.core.arm_factors(arm)
            )
            return {
                **manifest,
                "arm_id": arm,
                "training_seed": seed,
                "factors": factors,
            }
        return donor or {"reward_function_sha256": "reward-sha"}

    monkeypatch.setattr(core, "_read_hashed_json", fake_read)

    def fake_sha(path: Path) -> str:
        if "base_state" in str(path):
            return "base-sha"
        return "x-sha"

    monkeypatch.setattr(core, "_sha256_file", fake_sha)
    monkeypatch.setattr(core, "_relative", lambda path: str(path))
    monkeypatch.setattr(core, "_write_new_json", lambda path, payload: "written")
    return r476_out, out


def test_import_accepts_verified_r476_shards(monkeypatch, tmp_path) -> None:
    manifest = _import_manifest()
    _setup_import_trees(monkeypatch, tmp_path, manifest)
    monkeypatch.setattr(
        R477.base.base.core, "_assert_wsl_scratch", lambda: None
    )
    result = R477.import_r476_training_shards()
    assert result == "written"
    for arm, seed in R477.REUSED_CELLS:
        target_dir = R477.OUT / "train" / arm / f"seed{seed}"
        for name in ("manifest.json", "half.pt", "final.pt", "full_curves.npz"):
            assert (target_dir / name).is_file()
            assert (target_dir / f"{name}.sha256").is_file()
            source_stat = os.stat(R477.R476_OUT / "train" / arm / f"seed{seed}" / name)
            target_stat = os.stat(target_dir / name)
            assert source_stat.st_ino == target_stat.st_ino


def test_import_rejects_invalid_or_mismatched_manifest(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        R477.base.base.core, "_assert_wsl_scratch", lambda: None
    )
    for bad, keep_factors in (
        (_import_manifest(valid=False), False),
        (_import_manifest(round_id="R475"), False),
        (_import_manifest(factors_ok=False), True),
    ):
        _setup_import_trees(monkeypatch, tmp_path, bad, keep_factors=keep_factors)
        with pytest.raises(RuntimeError):
            R477.import_r476_training_shards()


def test_import_phase_runs_donors_then_shards(monkeypatch) -> None:
    events = []

    monkeypatch.setattr(R477.base, "import_parent_artifacts", lambda: events.append("donors"))
    monkeypatch.setattr(R477, "import_r476_training_shards", lambda: events.append("shards"))
    R477.import_parent_artifacts()
    assert events == ["donors", "shards"]


def test_missing_shards_covers_all_48_cells(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(R477, "OUT", tmp_path)
    missing = R477.missing_shards()
    assert len([item for item in missing if item.startswith("train|")]) == 48
    for arm, seed in (*R477.REUSED_CELLS, *R477.RETRAIN_CELLS):
        (tmp_path / "train" / arm / f"seed{seed}").mkdir(parents=True)
        (tmp_path / "train" / arm / f"seed{seed}" / "manifest.json").write_text(
            "{}", encoding="utf-8"
        )
    remaining = [item for item in R477.missing_shards() if item.startswith("train|")]
    assert remaining == []


def test_r477_paths_do_not_reuse_r476_output() -> None:
    assert "r477" in R477.OUT.as_posix()
    assert "r476" not in R477.OUT.as_posix()
    assert R477.ROUND_ID == "R477"
    assert R477.PLAN == Path(R477.ROOT, "memory/rounds/R477/plan.md")


def test_pipeline_runs_two_waves_then_eval_and_finalization() -> None:
    pipeline = R477.PIPELINE.read_text(encoding="utf-8")
    assert "r477_train_wave${wave}_shards.json" in pipeline
    assert "for wave in 1 2" in pipeline
    assert "for wave in 1 2 3" not in pipeline
    assert "eta-recalibration" in pipeline
    assert "trap 'on_signal 143' TERM" in pipeline
    assert "run_r477_u2_confirmatory.py inventory" in pipeline
    assert "run_phase budget" in pipeline
    assert "run_phase aggregate" in pipeline
    assert "run_phase manifest" in pipeline
    assert "expected 48 training manifests" in pipeline


def test_source_rows_delegates_frozen_row_permutation() -> None:
    joint = np.arange(28, dtype=np.float32).reshape(4, 7)
    rows = R477.source_rows(joint, "P")
    assert np.array_equal(rows[:, :3], joint[:, :3])
    for index in range(4):
        assert np.array_equal(rows[index, 3:7], joint[(index + 1) % 4, 3:7])
