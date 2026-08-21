"""Runner tests for the R395 second science-identical correction."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r395_ppvsm1_object_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r395_runner_test", path)
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
        self.Pref = SimpleNamespace(v=np.asarray([7.0, 7.5]))
        self.Qref = SimpleNamespace(v=np.asarray([1.0, 1.5]))


class _System:
    def __init__(self):
        self.Bus = _Bus()
        self.PPVSM1 = _Ppvsm1()
        y = np.arange(10, dtype=float) * 0.1  # y0=0.0 y1=0.1 ... y9=0.9
        x = np.asarray([1.0, 1.0], dtype=float)
        self.dae = SimpleNamespace(t=0.0, x=x, y=y)


def test_contract_carries_correction_provenance() -> None:
    module = _load_runner()
    contract = module.build_r395_contract()
    assert contract["round"] == "R395"
    assert contract["parent_round"] == "R394"
    assert contract["evidence_corrections"] == [
        "global_dae_address_variable_readback",
        "pre_init_static_post_init_pref_reference_timing",
    ]
    assert contract["parameter_card"]["mf"] == 0.15


def test_initial_trace_row_reads_global_dae_by_global_address() -> None:
    module = _load_runner()
    system = _System()
    row = module._initial_trace_row(system)
    assert row["bus_v"] == {"1": 0.0, "2": 0.1}
    assert row["devices"]["PPVSM1_1"]["Pe"] == 0.2
    assert row["devices"]["PPVSM1_2"]["Iq"] == 0.9
    assert row["devices"]["PPVSM1_1"]["virtual_frequency"] == 1.0


def test_reference_rows_combine_pre_init_static_with_post_init_pref() -> None:
    module = _load_runner()
    static_rows = [
        {"idx": "PPVSM1_1", "static_p": 7.0, "static_q": 1.0},
        {"idx": "PPVSM1_2", "static_p": 7.5, "static_q": 1.5},
    ]
    pref_qref = {
        "PPVSM1_1": (7.0, 1.0),
        "PPVSM1_2": (7.5, 1.5),
    }
    rows = module._reference_rows(static_rows, pref_qref)
    assert all(row["abs_deviation"] == 0.0 for row in rows)
    pref_qref["PPVSM1_1"] = (7.2, 1.0)
    rows = module._reference_rows(static_rows, pref_qref)
    assert rows[0]["abs_deviation"] == pytest.approx(0.2)


def test_parent_chain_rejects_tampered_manifest() -> None:
    module = _load_runner()
    contract = module.build_r395_contract()
    assert module.validate_r394_parent_chain(contract) is True
    tampered = dict(contract)
    tampered["parent_r394_sha256"] = {
        **contract["parent_r394_sha256"],
        "seal": "0" * 64,
    }
    assert module.validate_r394_parent_chain(tampered) is False
