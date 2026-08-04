from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes" / "r307_eval_metadata_amendment.py"


def _load_probe():
    spec = importlib.util.spec_from_file_location("r307_eval_metadata_amendment", PROBE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r307_eval_amendment_changes_only_scenario_sign_and_adds_source_binding() -> None:
    probe = _load_probe()
    source = {
        "round": "R307",
        "question": "Q-0063",
        "coordinate": "edge_1",
        "controller": "negative",
        "sign": "negative",
        "traces": [{"t": 0.7, "bess_requested_power_system_pu": [0.0] * 4}],
    }
    original = deepcopy(source)

    amended = probe.normalize_eval_record(
        source,
        source_path="results/r307/edge.json",
        source_sha256="a" * 64,
    )

    assert source == original
    assert amended["sign"] == "paired"
    assert amended["pulse_sign"] == "negative"
    assert amended["source_record"] == {
        "path": "results/r307/edge.json",
        "sha256": "a" * 64,
    }
    comparable = deepcopy(amended)
    comparable["sign"] = comparable.pop("pulse_sign")
    comparable.pop("source_record")
    assert comparable == original
