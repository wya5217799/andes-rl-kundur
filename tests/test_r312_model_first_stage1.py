from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r312_model_first_stage1.py"


def _module():
    spec = importlib.util.spec_from_file_location("r312_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R312 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r312_contract_is_fresh_guarded_and_nonlearning() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R312"
    assert contract["question"] == "Q-0068"
    assert contract["trace_count"] == 27
    assert contract["fresh_execution_required"] is True
    assert contract["forbidden_source_rounds"] == ["R307", "R308", "R310"]
    assert contract["eval"]["trigger"] == {
        "run_manifest_trace_count": 27,
        "verified_edge_record_count": 18,
        "source_sidecars_required": True,
    }
    assert contract["eval"]["guard_synthesis"] == {
        "source": "authoritative Stage-1 source fields",
        "mapping": {
            "completed": True,
            "tds_test_ok": True,
            "system_exit_code": 0,
            "finite_telemetry": True,
        },
        "fail_closed": True,
    }
    assert contract["eval"]["bootstrap_resamples"] == 10_000
    assert contract["eval"]["bootstrap_seed"] == 2026080312
    assert contract["eval"]["evidence_status"] == "EXTERNAL_AUTHORITY_REQUIRED"
    assert contract["predictor_fitting_authorized"] is False
    assert contract["controller_development_authorized"] is False
    assert contract["training_authorized"] is False


def test_r312_parser_exposes_only_prepare_run_eval_analyse() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "run", "eval", "analyse"}


def test_r312_json_writer_is_create_only(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "artifact.json"

    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
