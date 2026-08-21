"""Runner tests for the R393 PPVSM1 object gate.

Import the runner module (no ANDES execution) and lock the frozen seams.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r393_ppvsm1_object_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r393_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakePpvsm1:
    def __init__(self) -> None:
        self.n = 2
        self.idx = SimpleNamespace(v=["PPVSM1_1", "PPVSM1_2"])

    def get(self, *, src, idx, attr):
        if src == "bus":
            return {"PPVSM1_1": 1, "PPVSM1_2": 2}[idx]
        if src == "gen":
            return {"PPVSM1_1": 1, "PPVSM1_2": 2}[idx]
        if src == "Pref":
            return 2.0
        if src == "Qref":
            return 0.5
        raise KeyError(src)


class _FakeStaticGen:
    @staticmethod
    def get(*, src, idx, attr):
        if src == "p":
            return 2.0
        if src == "q":
            return 0.5
        raise KeyError(src)


class _FakeSystem:
    def __init__(self) -> None:
        self.PPVSM1 = _FakePpvsm1()
        self.StaticGen = _FakeStaticGen()


def test_contract_binds_two_unit_card() -> None:
    module = _load_runner()
    contract = module.build_ppvsm1_object_contract()
    assert contract["parameter_card"]["krho"] == 20.0
    assert contract["runtime_parameter_card"]["xf"] == pytest.approx(
        0.2 * 100.0 / 900.0
    )
    assert contract["allowed_zero_modes"] == 1


def test_source_manifest_covers_model_builder_and_classifier() -> None:
    module = _load_runner()
    sources = module.source_manifest()
    assert sources["model"]["path"].endswith("ppvsm1.py")
    assert sources["builder"]["path"].endswith("ppvsm1_static_kundur.py")
    assert sources["classifier"]["path"].endswith("ppvsm1_object_gate.py")


def test_parent_manifest_binds_stopping_evidence() -> None:
    module = _load_runner()
    parents = module.parent_manifest()
    assert "clm1100" in parents
    assert "clm1105" in parents
    assert "r391_analysis" in parents
    assert "r392_analysis" in parents


def test_source_snapshot_rows() -> None:
    module = _load_runner()
    contract = module.build_ppvsm1_object_contract()
    system = _FakeSystem()
    rows = module._source_snapshot(system, contract)
    assert [row["idx"] for row in rows] == ["PPVSM1_1", "PPVSM1_2"]
    assert all(row["abs_deviation"] == 0.0 for row in rows)


def test_record_carries_frozen_schema() -> None:
    module = _load_runner()
    record = module._empty_record("abc")
    assert record["round"] == "R393"
    assert record["trajectory_count"] == 0
    assert record["spectrum"]["captured"] is False
    assert record["solver"]["tds_tolerance"] == 1e-4
