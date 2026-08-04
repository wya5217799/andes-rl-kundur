from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r320_pole_cause.py"


def _module():
    spec = importlib.util.spec_from_file_location("r320_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R320 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r320_contract_freezes_one_template_and_no_performance_access() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R320"
    assert contract["question"] == "Q-0075"
    assert contract["radius_identity_tolerance"] == 1.0e-12
    assert contract["relative_rank_and_pbh_tolerance"] == 1.0e-10
    assert contract["placement_target_tolerance"] == 1.0e-8
    assert len(contract["controller_target_poles"]) == 14
    assert len(contract["observer_target_poles"]) == 14
    assert np.isclose(max(contract["controller_target_poles"]), 0.98)
    assert np.isclose(max(contract["observer_target_poles"]), 0.94)
    assert contract["performance_case_access"] == "PROHIBITED"
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["training_authorized"] is False


def test_r320_parser_exposes_no_performance_or_physical_command_and_is_create_only(
    tmp_path: Path,
) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "diagnose", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
