from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r319_observer_lqr.py"


def _module():
    spec = importlib.util.spec_from_file_location("r319_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R319 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r319_contract_freezes_one_design_equal_budget_and_model_only_scope() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R319"
    assert contract["question"] == "Q-0074"
    assert "scalar_candidates" not in contract
    assert contract["synthesis_count_per_point_and_arm"] == 1
    assert contract["development_case_count"] == 32
    assert contract["examination_case_count"] == 80
    assert contract["maximum_pole_radius"] == 0.995
    assert contract["minimum_improvement"] == 0.02
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r319_cases_and_mismatch_transforms_match_the_frozen_counts() -> None:
    module = _module()

    assert len(module.development_cases()) == 32
    assert len(module.examination_cases()) == 16
    transforms = module.mismatch_transforms()
    assert set(transforms) == {
        "nominal",
        "plus_scale",
        "minus_scale",
        "signed_reflection",
        "common_differential_exchange",
    }
    for name, transform in transforms.items():
        expected = 0.0 if name == "nominal" else 0.15
        assert np.isclose(np.linalg.norm(transform, ord=2), expected)


def test_r319_parser_exposes_no_physical_or_eval_command_and_writes_create_only(
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
