"""Contract tests for the prospective R329 formal adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r329_disturbance_estimator.py"


def _module():
    spec = importlib.util.spec_from_file_location("r329_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R329 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r329_contract_freezes_one_estimator_and_forbids_holdout() -> None:
    contract = _module().build_contract()
    estimator = contract["estimator"]

    assert contract["round"] == "R329"
    assert contract["question"] == "Q-0082"
    assert contract["development_case_count"] == 32
    assert estimator["kind"] == "fixed-disturbance-augmented-steady-state"
    assert estimator["candidate_count"] == 1
    assert estimator["disturbance_scale"] == 0.05
    assert estimator["measurement_fraction"] == 0.01
    assert estimator["holdout_access"] == "forbidden"


def test_r329_execute_replays_development_and_never_opens_holdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    calls: list[int] = []
    written: dict[str, object] = {}
    seal = {
        "contract_payload_sha256": "c" * 64,
        "parent": {
            "r326_execution": {"sha256": "e" * 64},
            "r327_analysis": {"sha256": "a" * 64},
            "r328_execution": {"sha256": "o" * 64},
        },
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))
    monkeypatch.setattr(
        module,
        "_formal_designs",
        lambda: ({"HS0": object()}, {"HS0": object()}, {"HS0": object()}),
    )

    def fake_pass(*_args):
        calls.append(len(calls))
        return [{"arm": "retained_cross", "case": "c"}]

    monkeypatch.setattr(module, "_development_pass", fake_pass)
    monkeypatch.setattr(
        module,
        "_design_records",
        lambda *_: {"HS0": {"finite": True}},
    )
    monkeypatch.setattr(
        module,
        "_write_new_json",
        lambda _path, payload: written.update(payload) or "d" * 64,
    )

    module.execute(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert calls == [0, 1]
    assert written["deterministic_execution_replay"] is True
    assert written["holdout_accessed"] is False
    assert written["estimator_information_boundary"] is True


def test_r329_parser_and_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
