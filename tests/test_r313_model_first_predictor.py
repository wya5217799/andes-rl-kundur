from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r313_model_first_predictor.py"


def _module():
    spec = importlib.util.spec_from_file_location("r313_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R313 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r313_contract_freezes_unseen_bank_comparison_and_no_training() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R313"
    assert contract["question"] == "Q-0069"
    assert contract["training_source"] == {
        "round": "R312",
        "question": "Q-0068",
        "trace_count": 27,
        "required_classification": "STAGE1-PASS",
    }
    assert contract["holdout_operating_points"] == [
        {
            "name": "HP0",
            "vsg_m_device": 200.0,
            "vsg_d_device": 100.0,
            "tie_rx_scale": 1.25,
            "initial_soc": 0.50,
            "training_weights": {"OP0": 0.50, "OP1": 0.25, "OP2": 0.25},
        },
        {
            "name": "HP1",
            "vsg_m_device": 180.0,
            "vsg_d_device": 90.0,
            "tie_rx_scale": 1.20,
            "initial_soc": 0.42,
            "training_weights": {"OP0": 0.20, "OP1": 0.60, "OP2": 0.20},
        },
    ]
    assert contract["holdout_amplitudes_system_pu"] == [0.025, 0.065]
    assert contract["holdout_trace_count"] == 34
    assert contract["eval"]["trigger"] == {
        "run_manifest_trace_count": 34,
        "verified_edge_record_count": 24,
        "source_sidecars_required": True,
    }
    assert contract["thresholds"] == {
        "total_nrmse_max": 0.15,
        "peak_magnitude_relative_error_max": 0.10,
        "peak_timing_error_seconds_max": 0.2,
        "aggregate_cross_squared_error_reduction_min": 0.20,
        "cross_record_win_fraction_min": 0.75,
    }
    assert contract["comparison_identifiability"]["decision"] == "ALLOW"
    assert contract["controller_development_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r313_parser_exposes_only_sealed_lifecycle_commands() -> None:
    parser = _module().build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "fit", "run", "eval", "analyse"}


def test_r313_json_writer_is_create_only(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "artifact.json"

    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    assert path.with_suffix(".json.sha256").is_file()
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
