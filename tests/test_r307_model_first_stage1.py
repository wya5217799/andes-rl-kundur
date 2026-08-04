from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r307_model_first_stage1.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("run_r307_model_first_stage1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r307_contract_freezes_27_traces_and_one_second_eval_window() -> None:
    adapter = _load_adapter()

    contract = adapter.build_contract()

    assert contract["round"] == "R307"
    assert contract["question"] == "Q-0063"
    assert contract["trace_count"] == 27
    assert contract["active_steps"] == 5
    assert contract["recovery_steps"] == 20
    assert contract["eval"] == {
        "execution_profile": "vector_power",
        "required_active_window_seconds": 1.0,
        "edge_trace_count": 18,
        "evidence_status": "EXTERNAL_AUTHORITY_REQUIRED",
    }
    assert contract["training_authorized"] is False


def test_r307_parser_exposes_only_prepare_run_eval_and_analyse() -> None:
    adapter = _load_adapter()
    parser = adapter.build_parser()

    assert parser.parse_args(["prepare"]).command == "prepare"
    for command in ("run", "eval", "analyse"):
        assert parser.parse_args(
            [command, "--expected-seal-sha256", "0" * 64]
        ).command == command
    with pytest.raises(SystemExit):
        parser.parse_args(["train"])


def test_r307_writer_is_create_only_and_hash_checked(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "artifact.json"

    digest = adapter._write_new_json(path, {"round": "R307"})

    assert digest == adapter._sha256_file(path)
    with pytest.raises(FileExistsError, match="already exists"):
        adapter._write_new_json(path, {"round": "R307"})
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sidecar mismatch"):
        adapter._read_verified_json(path)
