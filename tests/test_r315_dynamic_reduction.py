from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r315_dynamic_reduction.py"


def _module():
    spec = importlib.util.spec_from_file_location("r315_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R315 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r315_contract_freezes_one_reduction_and_off_template_bank() -> None:
    contract = _module().build_contract()

    assert contract["round"] == "R315"
    assert contract["question"] == "Q-0071"
    assert contract["realization"] == {
        "kind": "era",
        "order": 10,
        "block_rows": 8,
        "block_columns": 8,
        "markov_horizon_steps": 25,
        "sample_period_seconds": 0.2,
        "state_initialization": "zero",
        "maximum_spectral_radius": 0.995,
        "pole_projection": "clip-magnitude-only-before-holdout",
    }
    assert contract["holdout_trace_count"] == 50
    assert contract["eval"]["trigger"]["verified_edge_record_count"] == 36
    assert contract["excitation_shapes"] == {
        "impulse": [0.05],
        "triangle": [0.02, 0.04, 0.05, 0.04, 0.02],
        "bipolar": [0.05, 0.05, 0.0, -0.05, -0.05],
    }
    assert contract["comparison_identifiability"]["reduced_full_vs_block"] == "ALLOW"
    assert contract["comparison_identifiability"]["R314_vs_R315"] == "QUALIFY"
    assert contract["controller_development_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r315_parser_and_create_only_writer_preserve_the_sealed_lifecycle(
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
