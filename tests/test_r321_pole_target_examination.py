"""Contract tests for the R321 create-only execution adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r321_pole_target_examination.py"


def _module():
    spec = importlib.util.spec_from_file_location("r321_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R321 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r321_contract_freezes_exact_targets_scales_cases_and_comparison() -> None:
    module = _module()
    contract = module.build_contract()

    assert contract["round"] == "R321"
    assert contract["question"] == "Q-0076"
    assert contract["parent_rounds"] == ["R316", "R319", "R320"]
    assert len(contract["controller_target_poles"]) == 14
    assert len(contract["observer_target_poles"]) == 14
    assert np.isclose(max(contract["controller_target_poles"]), 0.98)
    assert np.isclose(max(contract["observer_target_poles"]), 0.94)
    assert contract["placement_target_tolerance"] == 1.0e-8
    assert contract["placement_call_count_per_point_and_arm"] == 1
    assert contract["tuning_candidate_count"] == 0
    assert contract["output_scales"] == {
        "HS0": [
            0.0002668112041645563,
            0.00015882926554077416,
            0.00019288206508276265,
            0.0002124274132893341,
        ],
        "HS1": [
            0.00025989821599602683,
            0.00014880082973969276,
            0.00018244950507686816,
            0.00020106658488483798,
        ],
    }
    assert contract["action_scales"] == [0.36, 0.36, 0.36, 0.36]
    assert len(module.development_cases()) == 32
    assert len(module.examination_cases()) == 16
    assert len(module.mismatch_transforms()) == 5
    assert contract["examination_case_count"] == 80
    assert contract["comparison_identifiability"]["decision"] == "ALLOW"
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r321_parser_exposes_only_seal_execute_analyse_and_is_create_only(
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
