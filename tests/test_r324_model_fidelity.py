from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from probes.r324_model_fidelity_validation import REQUIRED_PARAMETER_IDS

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r324_model_fidelity.py"


def _module():
    spec = importlib.util.spec_from_file_location("r324_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R324 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r324_contract_freezes_parameter_inventory_and_three_refinements() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R324"
    assert contract["question"] == "Q-0079"
    assert {row["id"] for row in contract["parameter_bindings"]} == set(
        REQUIRED_PARAMETER_IDS
    )
    assert contract["execution"] == {
        "operating_point": "OP0",
        "coordinate": "edge_2",
        "sign": "negative",
        "pulse_system_pu": [0.0, 0.0, -0.05, 0.05],
        "active_steps": 5,
        "recovery_steps": 20,
        "control_period_seconds": 0.2,
        "tds_substeps": [5, 10, 20],
        "tds_max_segment_seconds": [0.04, 0.02, 0.01],
        "tds_method": "trapezoid",
        "initialization_tolerance": 1e-4,
        "initialization_tiny_correction_threshold": 1e-10,
        "dynamic_tolerance": 1e-10,
        "dynamic_tiny_correction_threshold": 1e-16,
    }
    assert contract["controller_executed"] is False
    assert contract["eval_status"] == "NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE"
    assert contract["training_authorized"] is False


def test_r324_parser_is_create_only_prepare_execute_analyse() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}


def test_r324_json_writer_is_create_only(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "artifact.json"

    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
