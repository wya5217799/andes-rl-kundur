"""Contract tests for the R327 reference-recovery adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r327_reference_recovery.py"


def _module():
    spec = importlib.util.spec_from_file_location("r327_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R327 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r327_contract_is_exact_eight_row_no_holdout_amendment() -> None:
    contract = _module().build_contract()
    recovery = contract["reference_recovery"]

    assert contract["round"] == "R327"
    assert contract["question"] == "Q-0080"
    assert len(recovery["expected_keys"]) == 8
    assert recovery["worker_count"] == 1
    assert recovery["native_numerical_threads"] == 24
    assert recovery["design_transfer"] == "none-rebuild-locally-per-arm"
    assert recovery["holdout_access"] == "forbidden"


def test_r327_fresh_worker_receives_no_model_or_design_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    calls: list[tuple[object, tuple[object, ...]]] = []

    class Future:
        def result(self):
            return [{"ok": True}]

    class Executor:
        def __init__(self, **kwargs):
            assert kwargs["max_workers"] == 1

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def submit(self, fn, *args):
            calls.append((fn, args))
            return Future()

    monkeypatch.setattr(module, "ProcessPoolExecutor", Executor)

    assert module._fresh_reference_pass() == [{"ok": True}]
    assert calls == [(module._reference_recovery_pass, ())]


def test_r327_execute_runs_two_fresh_passes_and_never_accesses_holdout(
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
            "r326_analysis": {"sha256": "a" * 64},
        },
    }
    monkeypatch.setattr(module, "_load_seal", lambda *_: (seal, "s" * 64))

    def fake_pass():
        calls.append(len(calls))
        return [{"arm": "retained_cross", "case": "c", "mismatch": "nominal"}]

    monkeypatch.setattr(module, "_fresh_reference_pass", fake_pass)
    monkeypatch.setattr(
        module,
        "_write_new_json",
        lambda _path, payload: written.update(payload) or "d" * 64,
    )

    module.execute(tmp_path / "seal.json", "s" * 64, tmp_path)

    assert calls == [0, 1]
    assert written["deterministic_reference_replay"] is True
    assert written["holdout_accessed"] is False
    assert written["parent_identity"] is True


def test_r327_parser_and_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})
