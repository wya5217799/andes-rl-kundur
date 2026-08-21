"""Runner tests for the R396 third science-identical correction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r396_ppvsm1_object_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r396_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Var:
    def __init__(self, v_code):
        self.v_code = v_code
        self.a = [0, 1]


class _Bus:
    def __init__(self):
        self.idx = SimpleNamespace(v=["1", "2"])
        self.v = _Var("y")
        self.v.a = [0, 1]


class _Ppvsm1:
    def __init__(self):
        self.idx = SimpleNamespace(v=["PPVSM1_1", "PPVSM1_2"])
        self.Pe = _Var("y")
        self.Pe.a = [2, 3]
        self.Qe = _Var("y")
        self.Qe.a = [4, 5]
        self.Id = _Var("y")
        self.Id.a = [6, 7]
        self.Iq = _Var("y")
        self.Iq.a = [8, 9]
        self.INTw_y = _Var("x")
        self.INTw_y.a = [0, 1]


class _System:
    def __init__(self):
        self.Bus = _Bus()
        self.PPVSM1 = _Ppvsm1()
        y = np.arange(10, dtype=float) * 0.1
        x = np.asarray([1.0, 1.0], dtype=float)
        self.dae = SimpleNamespace(t=0.0, x=x, y=y)


def test_contract_carries_correction_provenance() -> None:
    module = _load_runner()
    contract = module.build_r396_contract()
    assert contract["round"] == "R396"
    assert contract["parent_round"] == "R395"
    assert contract["evidence_corrections"] == ["signal_major_initial_trace_shape"]


def test_initial_trace_row_is_signal_major() -> None:
    module = _load_runner()
    system = _System()
    row = module._initial_trace_row(system)
    assert set(row["devices"]) == {"Pe", "Qe", "Id", "Iq", "virtual_frequency"}
    assert row["devices"]["Pe"]["PPVSM1_1"] == 0.2
    assert row["devices"]["Iq"]["PPVSM1_2"] == 0.9
    assert row["devices"]["virtual_frequency"]["PPVSM1_1"] == 1.0
    assert row["bus_v"] == {"1": 0.0, "2": 0.1}


def test_parent_chain_valid_and_tamper_rejected() -> None:
    module = _load_runner()
    contract = module.build_r396_contract()
    assert module.validate_r395_parent_chain(contract) is True
    tampered = dict(contract)
    tampered["parent_r395_sha256"] = {
        **contract["parent_r395_sha256"],
        "seal": "0" * 64,
    }
    assert module.validate_r395_parent_chain(tampered) is False
