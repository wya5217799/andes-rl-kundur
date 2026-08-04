"""Contract tests for the R325 constrained-horizon execution adapter."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r325_constrained_horizon.py"


def _module():
    spec = importlib.util.spec_from_file_location("r325_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R325 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r325_contract_freezes_one_constrained_candidate_and_fresh_holdout() -> None:
    module = _module()
    contract = module.build_contract()

    assert contract["round"] == "R325"
    assert contract["question"] == "Q-0078"
    assert contract["r321_analysis_access"] == "HASH-ONLY-NO-PARSE"
    assert contract["controller"]["horizon_steps"] == 25
    assert contract["controller"]["weight_candidate_count"] == 0
    assert contract["controller"]["horizon_candidate_count"] == 0
    assert contract["solver"]["maximum_iterations"] == 200
    assert len(module.development_cases()) == 32
    assert contract["holdout_base_case_count"] == 16
    assert contract["holdout_mismatch_mode_count"] == 5
    assert contract["holdout_case_count"] == 80
    assert contract["comparison_identifiability"]["decision"] == "ALLOW"
    assert contract["eval"] == "NOT-APPLICABLE-MODEL-ONLY"
    assert contract["physical_execution_authorized"] is False
    assert contract["distributed_agent_implementation_authorized"] is False
    assert contract["training_authorized"] is False


def test_r325_parser_and_json_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})


def test_r325_adapter_never_parses_the_protected_r321_analysis() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    forbidden_calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.func, ast.Name) or node.func.id != "_read_verified_json":
            continue
        if isinstance(node.args[0], ast.Name) and node.args[0].id == "R321_ANALYSIS":
            forbidden_calls.append(node)

    assert forbidden_calls == []


def test_r325_execute_reruns_the_controller_before_replay_passes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    calls: list[int] = []
    written: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "_load_seal",
        lambda _path, _expected: ({"contract": {}}, "a" * 64),
    )

    def fake_execute(_seal, _digest, *, created_utc):
        calls.append(len(calls) + 1)
        return {"created_utc": created_utc, "measurement": calls[-1]}

    def fake_write(_path, payload):
        written.update(payload)
        return "b" * 64

    monkeypatch.setattr(module, "_execute_payload", fake_execute)
    monkeypatch.setattr(module, "_write_new_json", fake_write)

    module.execute(tmp_path / "seal.json", "a" * 64, tmp_path)

    assert calls == [1, 2]
    assert written["deterministic_execution_replay"] is False
