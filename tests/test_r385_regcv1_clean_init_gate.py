from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r385_regcv1_clean_init_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r385", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_exposes_only_rehearsal_seal_and_formal_execution() -> None:
    runner = _load_runner()
    parser = runner.build_parser()
    subparsers = next(
        action
        for action in parser._actions
        if action.__class__.__name__ == "_SubParsersAction"
    )
    assert set(subparsers.choices) == {"rehearse", "prepare", "execute"}


def test_create_only_json_refuses_overwrite(tmp_path: Path) -> None:
    runner = _load_runner()
    target = tmp_path / "artifact.json"
    runner.write_new_json(target, {"round": "R385"})
    with pytest.raises(FileExistsError):
        runner.write_new_json(target, {"round": "R385", "retry": True})


def test_capacity_is_serial_and_never_formal_authority() -> None:
    runner = _load_runner()
    payload = runner.build_capacity_payload(
        logical_processors=32,
        physical_memory_bytes=32_000_000_000,
        wsl_memory_available_bytes=16_000_000_000,
        disk_free_bytes=100_000_000_000,
        competing_processes=[],
    )

    assert payload["readiness"] == "RUN-READY"
    assert payload["wsl_python_processes"] == 1
    assert payload["native_threads_per_process"] == 1
    assert payload["formal_authority"] is False


def test_forbidden_dae_names_detects_andes_variable_first_names() -> None:
    runner = _load_runner()
    system = SimpleNamespace(
        dae=SimpleNamespace(
            xy_name=["delta GENROU 1", "LL_y TGOV1 1", "v Bus 1"]
        )
    )

    assert runner.forbidden_dae_names(system, ["GENROU", "TGOV1"]) == [
        "delta GENROU 1",
        "LL_y TGOV1 1",
    ]
