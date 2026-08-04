from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r316_dynamic_reduction.py"


def _module():
    spec = importlib.util.spec_from_file_location("r316_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R316 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r316_contract_changes_only_the_guard_and_new_holdout_identity() -> None:
    module = _module()
    contract = module.build_contract()
    parent = module.R315_BASE.build_contract()

    assert contract["round"] == "R316"
    assert contract["question"] == "Q-0071"
    assert contract["execution_guard_repair"] == {
        "nonzero_achieved_relative_error_max": 0.05,
        "zero_request_achieved_power_abs_max_system_pu": 1e-6,
        "request_command_readback_abs_tolerance_system_pu": 1e-12,
        "source_round": "R315",
        "source_claim": "CLM-0785",
    }
    assert contract["holdout_operating_points"] == [
        {
            "name": "HS0",
            "vsg_m_device": 177.5,
            "vsg_d_device": 88.75,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.41,
            "training_weights": {
                "OP0": 0.25,
                "OP1": 0.25,
                "OP2": 0.0,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP1", "HP1"],
        },
        {
            "name": "HS1",
            "vsg_m_device": 202.5,
            "vsg_d_device": 101.25,
            "tie_rx_scale": 1.35,
            "initial_soc": 0.51,
            "training_weights": {
                "OP0": 0.25,
                "OP1": 0.0,
                "OP2": 0.25,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP2", "HP1"],
        },
    ]
    assert contract["realization"] == parent["realization"]
    assert contract["excitation_shapes"] == parent["excitation_shapes"]
    assert contract["thresholds"] == parent["thresholds"]
    assert contract["holdout_trace_count"] == 50
    assert contract["eval"]["trigger"]["verified_edge_record_count"] == 36
    assert contract["controller_development_authorized"] is False
    assert contract["training_authorized"] is False


def test_r316_parser_and_create_only_writer_preserve_the_sealed_lifecycle(
    tmp_path: Path,
) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")
    assert set(action.choices) == {"prepare", "fit", "run", "eval", "analyse"}

    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
