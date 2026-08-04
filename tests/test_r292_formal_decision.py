from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r292_formal.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("run_r292_formal", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _effect(point: float, low: float, high: float) -> dict:
    return {
        "ratio_of_means_percent": {
            "point": point,
            "percentile_95_interval": [low, high],
        }
    }


def test_r292_decision_tree_distinguishes_superior_and_inferior() -> None:
    module = _load_script()
    endpoints = module.PRIMARY_ENDPOINTS

    distributed_q0 = {name: _effect(-5.0, -8.0, -2.1) for name in endpoints}
    central_q0 = {name: _effect(-6.0, -9.0, -3.0) for name in endpoints}
    distributed_central = {
        name: _effect(-3.0, -5.0, -0.5) for name in endpoints
    }
    assert module._classification(
        valid=True,
        distributed_vs_q0=distributed_q0,
        central_vs_q0=central_q0,
        distributed_vs_central=distributed_central,
        distributed_directional_seed_count=3,
    )["classification"] == "DISTRIBUTED-SUPERIOR"

    distributed_central = {
        name: _effect(4.0, 1.0, 7.0) for name in endpoints
    }
    assert module._classification(
        valid=True,
        distributed_vs_q0=distributed_q0,
        central_vs_q0=central_q0,
        distributed_vs_central=distributed_central,
        distributed_directional_seed_count=2,
    )["classification"] == "DISTRIBUTED-EFFECTIVE-INFERIOR"
