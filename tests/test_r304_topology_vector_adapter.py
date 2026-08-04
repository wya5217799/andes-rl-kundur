from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_r304_topology_vector_gate.py"


def _load_adapter():
    spec = importlib.util.spec_from_file_location("run_r304_topology_vector_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r304_adapter_is_import_safe_and_freezes_four_commands() -> None:
    adapter = _load_adapter()

    assert adapter.ROUND_ID == "R304"
    assert adapter.QUESTION_ID == "Q-0061"
    assert set(adapter.build_parser()._subparsers._group_actions[0].choices) == {
        "prepare",
        "run-shard",
        "eval-check",
        "analyse",
    }


def test_r304_three_shards_are_disjoint_and_cover_exactly_21_cells() -> None:
    adapter = _load_adapter()
    shards = [set(adapter._assigned_cells(index, 3)) for index in range(3)]

    assert [len(shard) for shard in shards] == [7, 7, 7]
    assert not (shards[0] & shards[1] or shards[0] & shards[2] or shards[1] & shards[2])
    assert set.union(*shards) == {
        (topology, action)
        for topology in adapter.gate.TOPOLOGY_ORDER
        for action in adapter.gate.ACTION_LIBRARY
    }


def test_r304_artifact_writer_is_create_only_with_sidecar(tmp_path: Path) -> None:
    adapter = _load_adapter()
    path = tmp_path / "artifact.json"

    digest = adapter._write_new_json(path, {"round": "R304"})

    assert json.loads(path.read_text(encoding="utf-8")) == {"round": "R304"}
    assert path.with_name("artifact.json.sha256").read_text(encoding="ascii") == (
        f"{digest}  artifact.json\n"
    )
    with pytest.raises(FileExistsError):
        adapter._write_new_json(path, {"round": "R304"})
