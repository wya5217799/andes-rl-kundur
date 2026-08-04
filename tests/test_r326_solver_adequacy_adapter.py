"""Contract tests for the prospective R326 execution adapter."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_r326_solver_adequacy.py"


def _module():
    spec = importlib.util.spec_from_file_location("r326_adapter", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R326 adapter")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_r326_contract_changes_only_the_prospective_solver_layer() -> None:
    module = _module()
    contract = module.build_contract()
    parent = module.r325.build_contract()
    changed = {"round", "question", "solver", "solver_repair", "classification"}

    assert contract["round"] == "R326"
    assert contract["question"] == "Q-0080"
    assert contract["solver"]["name"] == "osqp"
    assert contract["solver"]["version"] == "1.1.3"
    assert contract["solver"]["adaptive_rho_interval"] == 25
    assert contract["solver_repair"]["prefix_action_absolute_tolerance"] == 2.0e-5
    assert contract["solver_repair"]["prefix_output_absolute_tolerance"] == 1.0e-6
    assert contract["solver_repair"]["maximum_normalized_residual_ratio"] == 1.0
    for key, value in parent.items():
        if key not in changed:
            assert contract[key] == value


def test_r326_dependency_fingerprint_is_pinned_and_content_addressed() -> None:
    fingerprint = _module().dependency_fingerprint()

    assert fingerprint["osqp_version"] == "1.1.3"
    assert fingerprint["osqp_algebra"] == "builtin"
    assert len(fingerprint["osqp_distribution_sha256"]) == 64
    assert len(fingerprint["python_executable_sha256"]) == 64


def test_r326_parser_and_json_writer_are_create_only(tmp_path: Path) -> None:
    module = _module()
    parser = module.build_parser()
    action = next(item for item in parser._actions if item.dest == "command")

    assert set(action.choices) == {"prepare", "execute", "analyse"}
    path = tmp_path / "artifact.json"
    digest = module._write_new_json(path, {"ok": True})
    assert len(digest) == 64
    with pytest.raises(FileExistsError):
        module._write_new_json(path, {"ok": False})


def test_r326_execute_requires_replayed_development_before_holdout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    calls: list[str] = []
    written: dict[str, object] = {}
    monkeypatch.setattr(
        module,
        "_load_seal",
        lambda _path, _expected: ({"contract": {}}, "a" * 64),
    )

    def fake_development(_seal, _digest, *, created_utc):
        calls.append("development")
        return {"created_utc": created_utc, "measurement": len(calls)}

    monkeypatch.setattr(module, "_development_payload", fake_development)
    monkeypatch.setattr(module, "solver_development_allows_holdout", lambda *_: False)
    monkeypatch.setattr(
        module,
        "_write_new_json",
        lambda _path, payload: written.update(payload) or "b" * 64,
    )

    module.execute(tmp_path / "seal.json", "a" * 64, tmp_path)

    assert calls == ["development", "development"]
    assert written["deterministic_execution_replay"] is False
    assert written["holdout_accessed"] is False
