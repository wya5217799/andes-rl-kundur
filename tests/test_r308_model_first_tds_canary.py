from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r308_model_first_tds_canary.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location(
        "run_r308_model_first_tds_canary",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r308_contract_freezes_one_repair_and_two_traces() -> None:
    adapter = _load_adapter()

    contract = adapter.build_contract()

    assert contract["tds_convergence_tolerance"] == 1e-10
    assert contract["tds_tiny_correction_threshold"] == 1e-16
    assert contract["algebraic_residual_max"] == 1e-8
    assert contract["trace_bank"] == ["OP1/zero/zero", "OP1/edge_2/negative"]
    assert contract["parameter_sweep_authorized"] is False
    assert contract["full_stage1_authorized"] is False
    assert contract["training_authorized"] is False


def test_r308_parser_exposes_stable_prepare_run_eval_analyse_surface() -> None:
    adapter = _load_adapter()
    parser = adapter.build_parser()

    assert parser.parse_args(["prepare"]).command == "prepare"
    for command in ("run", "eval", "analyse"):
        assert parser.parse_args(
            [command, "--expected-seal-sha256", "0" * 64]
        ).command == command
    with pytest.raises(SystemExit):
        parser.parse_args(["sweep"])


def test_r308_writer_is_create_only_and_hash_checked(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "artifact.json"

    digest = adapter._write_new_json(path, {"round": adapter.ROUND_ID})

    assert digest == adapter._sha256_file(path)
    with pytest.raises(FileExistsError, match="create-only"):
        adapter._write_new_json(path, {"round": adapter.ROUND_ID})
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sidecar mismatch"):
        adapter._read_verified_json(path)
