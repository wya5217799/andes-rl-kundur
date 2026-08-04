from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r288_topology_information.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("r288_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_exposes_the_frozen_round_identity_and_commands() -> None:
    adapter = _load_adapter()

    assert adapter.ROUND_ID == "R288"
    assert adapter.QUESTION_ID == "Q-0047"
    assert adapter.DEFAULT_SEAL == (
        ROOT / "memory" / "rounds" / "R288" / "topology_information_seal.json"
    )
    assert adapter.DEFAULT_OUT == ROOT / "results" / "r288_topology_information"
    assert set(adapter.build_parser()._subparsers._group_actions[0].choices) == {
        "prepare",
        "run",
        "analyse",
    }


def test_probe_import_is_windows_safe_and_keeps_registered_contract() -> None:
    adapter = _load_adapter()
    probe = adapter._load_probe()

    assert probe.ROUND_ID == "R288"
    assert probe.QUESTION_ID == "Q-0047"
    assert probe.TOPOLOGY_COUNT == 3
    assert probe.POSITIVE_REAL_TOLERANCE == 1e-7
    assert tuple(probe.allocation_library()) == (
        "q0",
        "h1_pos",
        "h1_neg",
        "h2_pos",
        "h2_neg",
        "h3_pos",
        "h3_neg",
    )
    assert probe.DEFAULT_THRESHOLDS["headroom_max_min_percent"] == 5.0
    assert probe.DEFAULT_THRESHOLDS["headroom_mean_min_percent"] == 2.0
