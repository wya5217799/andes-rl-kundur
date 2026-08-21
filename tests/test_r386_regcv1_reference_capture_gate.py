from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r386_regcv1_reference_capture_gate.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_r386", RUNNER)
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


def test_formal_call_order_freezes_source_between_pflow_and_tds_init() -> None:
    runner = _load_runner()
    source = inspect.getsource(runner.run_formal_record)

    pflow = source.index("system.PFlow.run()")
    capture = source.index("capture_reference_source(system, contract)")
    tds_init = source.index("system.TDS.init()")
    post_init_compare = source.index("post_init_references(system, reference_source")
    assert pflow < capture < tds_init < post_init_compare


def test_execute_explicitly_routes_to_r386_create_only_root(monkeypatch) -> None:
    runner = _load_runner()
    observed = {}

    def fake_execute(*, expected_sha256, out_dir):
        observed.update(expected_sha256=expected_sha256, out_dir=out_dir)
        return "digest"

    monkeypatch.setattr(runner.base, "execute", fake_execute)

    assert runner.execute(expected_sha256="a" * 64) == "digest"
    assert observed == {
        "expected_sha256": "a" * 64,
        "out_dir": runner.DEFAULT_OUT,
    }
