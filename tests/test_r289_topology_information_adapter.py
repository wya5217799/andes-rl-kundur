from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r289_topology_information.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("r289_adapter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_adapter_freezes_multigraph_groups_and_round_identity() -> None:
    adapter = _load_adapter()
    kernel = adapter._load_kernel()

    assert kernel.ROUND_ID == "R289"
    assert kernel.QUESTION_ID == "Q-0047"
    assert adapter.TARGET_GROUPS == {
        "topology_1": (5, 6),
        "topology_2": (6, 7),
        "topology_3": (9, 10),
    }
    assert adapter.EXPECTED_SELECTED_LINES == ("Line_0", "Line_2", "Line_9")
    assert adapter.DEFAULT_SEAL == (
        ROOT / "memory" / "rounds" / "R289" / "topology_information_seal.json"
    )
    assert adapter.DEFAULT_OUT == ROOT / "results" / "r289_topology_information"


def test_adapter_records_parent_and_current_sources_without_copying_kernel() -> None:
    adapter = _load_adapter()
    kernel = adapter._load_kernel()

    sources = kernel._seal_sources()

    assert sources["adapter"]["path"] == "scripts/run_r289_topology_information.py"
    assert sources["parent_probe"]["path"] == "probes/r288_topology_information.py"
    assert sources["plan"]["path"] == "memory/rounds/R289/plan.md"
    assert sources["r288_structural_input"]["path"] == (
        "results/r288_topology_information/topology_inventory.json"
    )
    assert set(adapter.build_parser()._subparsers._group_actions[0].choices) == {
        "prepare",
        "run",
        "analyse",
    }
