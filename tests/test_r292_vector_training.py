from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "train_r292_vector_td3.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("train_r292_vector_td3", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r292_training_matrix_is_frozen_and_capacity_matched() -> None:
    module = _load_script()

    assert module.ROUND_ID == "R292"
    assert module.QUESTION_ID == "Q-0049"
    assert module.SEEDS == (101, 137, 173)
    assert module.ARCHITECTURES == ("central_vector", "distributed_edge")
    assert module._actor_parameter_counts() == {
        "central_vector": 4959,
        "distributed_edge": 4929,
    }
    for architecture in module.ARCHITECTURES:
        assert module._make_agent(architecture, "cpu").edge_count == 3
