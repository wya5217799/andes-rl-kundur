"""Contract tests for the R322 development-only execution adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r322_feedback_diagnosis.py"


def _module():
    spec = importlib.util.spec_from_file_location("r322_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R322 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r322_contract_freezes_development_only_diagnosis_and_one_scalar() -> None:
    module = _module()
    contract = module.build_contract()

    assert contract["round"] == "R322"
    assert contract["question"] == "Q-0077"
    assert contract["r321_analysis_access"] == "HASH-ONLY-NO-PARSE"
    assert contract["development_case_count"] == 32
    assert len(module.development_cases()) == 32
    assert not hasattr(module, "examination_cases")
    assert not hasattr(module, "mismatch_transforms")
    assert contract["decomposition_tolerance"] == 1.0e-10
    assert contract["observer_rescue_fraction"] == 0.50
    assert contract["true_state_authority_overdrive"] == 2.0
    assert contract["maximum_error_command_fraction"] == 0.50
    assert contract["repair"]["kind"] == "one-common-analytic-authority-scalar"
    assert contract["repair"]["tuning_candidate_count"] == 0
    assert contract["fresh_holdout_access"] == "PROHIBITED"
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["training_authorized"] is False


def test_r322_parser_is_create_only_and_exposes_no_holdout_or_physical_command(
    tmp_path: Path,
) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
