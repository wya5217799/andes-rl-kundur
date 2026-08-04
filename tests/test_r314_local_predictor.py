from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r314_local_predictor.py"


def _module():
    spec = importlib.util.spec_from_file_location("r314_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R314 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r314_contract_freezes_local_development_and_untouched_holdout() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R314"
    assert contract["question"] == "Q-0070"
    assert contract["development_sources"] == {
        "R312": {"question": "Q-0068", "trace_count": 27},
        "R313_HP1_only": {
            "question": "Q-0069",
            "trace_count": 17,
            "amplitudes_system_pu": [0.025, 0.065],
        },
        "forbidden_R313_operating_points": ["HP0"],
        "total_trace_count": 44,
    }
    assert contract["holdout_operating_points"] == [
        {
            "name": "HQ0",
            "vsg_m_device": 175.0,
            "vsg_d_device": 87.5,
            "tie_rx_scale": 1.10,
            "initial_soc": 0.40,
            "training_weights": {
                "OP0": 0.20,
                "OP1": 0.30,
                "OP2": 0.0,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP1", "HP1"],
        },
        {
            "name": "HQ1",
            "vsg_m_device": 205.0,
            "vsg_d_device": 102.5,
            "tie_rx_scale": 1.40,
            "initial_soc": 0.52,
            "training_weights": {
                "OP0": 0.20,
                "OP1": 0.0,
                "OP2": 0.30,
                "HP1": 0.50,
            },
            "simplex": ["OP0", "OP2", "HP1"],
        },
    ]
    assert contract["holdout_amplitudes_system_pu"] == [0.025, 0.065]
    assert contract["holdout_trace_count"] == 34
    assert contract["thresholds"] == {
        "total_nrmse_max": 0.15,
        "peak_magnitude_relative_error_max": 0.10,
        "peak_timing_error_seconds_max": 0.2,
        "aggregate_cross_squared_error_reduction_min": 0.20,
        "cross_record_win_fraction_min": 0.75,
    }
    assert contract["comparison_identifiability"]["local_full_vs_block"] == "ALLOW"
    assert contract["comparison_identifiability"]["R313_vs_R314"] == "QUALIFY"
    assert contract["controller_development_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r314_parser_and_create_only_writer_preserve_the_sealed_lifecycle(
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
