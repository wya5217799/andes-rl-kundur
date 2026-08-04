"""Contract tests for the R328 exact-state diagnostic adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r328_estimation_cause.py"


def _module():
    spec = importlib.util.spec_from_file_location("r328_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R328 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r328_contract_is_retained_development_only() -> None:
    contract = _module().build_contract()
    diagnosis = contract["estimation_diagnosis"]

    assert contract["round"] == "R328"
    assert contract["question"] == "Q-0081"
    assert contract["development_case_count"] == 32
    assert diagnosis["arm"] == "retained_cross"
    assert diagnosis["single_factor"] == "observer-estimate-to-exact-augmented-state"
    assert diagnosis["holdout_access"] == "forbidden"
    assert diagnosis["cross_deleted_oracle"] == "forbidden-nonidentifiable-state-basis"


def test_exact_augmented_state_is_plant_state_plus_previous_output() -> None:
    module = _module()
    state = np.arange(10, dtype=float)
    previous = np.arange(4, dtype=float) + 10.0

    augmented = module._exact_augmented_state(state, previous)

    np.testing.assert_array_equal(augmented[:10], state)
    np.testing.assert_array_equal(augmented[10:], previous)


def test_r328_execute_replays_development_and_never_opens_holdout(
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
        },
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))

    def fake_pass():
        calls.append(len(calls))
        return [{"arm": "retained_cross", "case": "c"}]

    monkeypatch.setattr(module, "_development_pass", fake_pass)
    monkeypatch.setattr(
        module,
        "_write_new_json",
        lambda _path, payload: written.update(payload) or "d" * 64,
    )

    module.execute(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert calls == [0, 1]
    assert written["deterministic_execution_replay"] is True
    assert written["holdout_accessed"] is False
    assert written["cross_deleted_oracle_accessed"] is False


def test_r328_parser_and_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
