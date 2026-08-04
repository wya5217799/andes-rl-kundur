from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r318_rejection_diagnosis.py"


def _module():
    spec = importlib.util.spec_from_file_location("r318_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R318 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r318_contract_replays_without_widening_or_performance_examination() -> None:
    module = _module()
    contract = module.build_contract()

    assert contract["round"] == "R318"
    assert contract["question"] == "Q-0073"
    assert contract["scalar_candidates"] == [value / 100.0 for value in range(1, 101)]
    assert contract["maximum_pole_radius"] == 0.995
    assert contract["development_case_count"] == 32
    assert contract["performance_selection_authorized"] is False
    assert contract["r317_examination_accessed"] is False
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["training_authorized"] is False


def test_r318_parser_has_no_physical_eval_or_optimization_command(
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
