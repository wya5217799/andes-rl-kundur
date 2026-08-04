from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r310_model_first_stage1.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("run_r310_model_first_stage1", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r310_contract_freezes_fresh_bank_solver_and_eval_rules() -> None:
    adapter = _load_adapter()

    contract = adapter.build_contract()

    assert contract["trace_count"] == 27
    assert contract["fresh_execution_required"] is True
    assert contract["forbidden_source_rounds"] == ["R307", "R308"]
    assert contract["solver"] == {
        "initialization_tolerance": 1e-4,
        "initialization_tiny_correction_threshold": 1e-10,
        "dynamic_tolerance": 1e-10,
        "dynamic_tiny_correction_threshold": 1e-16,
        "transition_count": 1,
    }
    assert contract["eval"]["trigger"] == {
        "run_manifest_trace_count": 27,
        "verified_edge_record_count": 18,
        "source_sidecars_required": True,
    }
    assert contract["eval"]["required_active_window_seconds"] == 1.0
    assert contract["eval"]["evidence_status"] == "EXTERNAL_AUTHORITY_REQUIRED"
    assert contract["optimization_rules"] == {
        "INVALID-STAGE1-EXECUTION": "new-cause-specific-canary-only",
        "STAGE1-AUTHORITY-NO-GO": "one-single-factor-nonlearning-diagnosis-or-stop",
        "STAGE1-PASS": "predictor-construction-in-separate-round-only",
    }
    assert contract["training_authorized"] is False


def test_r310_parser_exposes_only_prepare_run_eval_analyse() -> None:
    adapter = _load_adapter()
    parser = adapter.build_parser()

    assert parser.parse_args(["prepare"]).command == "prepare"
    for command in ("run", "eval", "analyse"):
        assert parser.parse_args(
            [command, "--expected-seal-sha256", "0" * 64]
        ).command == command
    with pytest.raises(SystemExit):
        parser.parse_args(["optimize"])


def test_r310_writer_is_create_only_and_hash_checked(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "artifact.json"

    digest = adapter._write_new_json(path, {"round": adapter.ROUND_ID})

    assert digest == adapter._sha256_file(path)
    with pytest.raises(FileExistsError, match="create-only"):
        adapter._write_new_json(path, {"round": adapter.ROUND_ID})
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(RuntimeError, match="sidecar mismatch"):
        adapter._read_verified_json(path)
