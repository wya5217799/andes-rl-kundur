"""Runner tests for the R394 science-identical correction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r394_ppvsm1_object_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r394_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Var:
    def __init__(self, values):
        self.v = np.asarray(values, dtype=float)
        self.a = [0] * len(values)
        self.v_code = "y"


class _Bus:
    def __init__(self):
        self.idx = SimpleNamespace(v=["1", "2"])
        self.v = _Var([1.0, 0.98])
        self.v.a = [0, 1]


class _Ppvsm1:
    def __init__(self):
        self.idx = SimpleNamespace(v=["PPVSM1_1", "PPVSM1_2"])
        self.Pe = _Var([2.0, 1.5])
        self.Pe.a = [0, 1]
        self.Qe = _Var([0.5, 0.4])
        self.Qe.a = [0, 1]
        self.Id = _Var([1.0, 0.8])
        self.Id.a = [0, 1]
        self.Iq = _Var([-0.3, -0.2])
        self.Iq.a = [0, 1]
        self.INTw_y = _Var([1.0, 1.0])
        self.INTw_y.a = [0, 1]


class _System:
    def __init__(self):
        self.Bus = _Bus()
        self.PPVSM1 = _Ppvsm1()
        self.dae = SimpleNamespace(t=0.0)


def test_contract_carries_correction_provenance() -> None:
    module = _load_runner()
    contract = module.build_r394_contract()
    assert contract["round"] == "R394"
    assert contract["parent_round"] == "R393"
    assert contract["evidence_corrections"] == [
        "initial_trace_variable_array_readback",
        "frozen_zero_point_two_second_tds_horizon",
        "pre_init_source_snapshot",
    ]
    assert contract["parameter_card"]["mf"] == 0.15


def test_initial_trace_row_reads_variable_arrays() -> None:
    module = _load_runner()
    system = _System()
    row = module._initial_trace_row(system)
    assert set(row["devices"]) == {"PPVSM1_1", "PPVSM1_2"}
    assert row["bus_v"] == {"1": 1.0, "2": 0.98}
    assert row["devices"]["PPVSM1_1"]["Pe"] == 2.0
    assert row["devices"]["PPVSM1_2"]["Iq"] == -0.2
    assert row["devices"]["PPVSM1_1"]["virtual_frequency"] == 1.0


def test_freeze_horizon_sets_registered_tf() -> None:
    module = _load_runner()
    contract = module.build_r394_contract()

    class _TdsConfig:
        tf = 20.0

    system = SimpleNamespace(TDS=SimpleNamespace(config=_TdsConfig()))
    value = module._freeze_horizon(system, contract)
    assert value == 0.2
    assert system.TDS.config.tf == 0.2


def test_parent_chain_rejects_tampered_manifest() -> None:
    module = _load_runner()
    contract = module.build_r394_contract()
    assert module.validate_r393_parent_chain(contract) is True
    tampered = dict(contract)
    tampered["parent_r393_sha256"] = {
        **contract["parent_r393_sha256"],
        "seal": "0" * 64,
    }
    assert module.validate_r393_parent_chain(tampered) is False
