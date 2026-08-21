from __future__ import annotations

from types import SimpleNamespace

import pytest

from andes_rl_kundur.env.andes.regcv1_kundur import (
    build_regcv1_kundur_object,
)


class _FakeModel:
    def __init__(self, *, idx, u, syn=None):
        self.idx = SimpleNamespace(v=list(idx))
        self.u = SimpleNamespace(v=list(u))
        self.n = len(idx)
        if syn is not None:
            self.syn = SimpleNamespace(v=list(syn))

    def set(self, name, idx, value, *, attr):
        assert name == "u"
        assert attr == "v"
        self.u.v[self.idx.v.index(idx)] = value


class _FakeStaticGen:
    n = 4

    @staticmethod
    def get(*, src, idx, attr):
        assert attr == "v"
        assert idx == [1, 2, 3, 4]
        if src == "bus":
            return [1.0, 2.0, 3.0, 4.0]
        if src == "Sn":
            return [900.0] * 4
        raise KeyError(src)


class _FakeSystem:
    def __init__(self, *, line_count: int = 15):
        self.Bus = SimpleNamespace(n=10)
        self.Line = SimpleNamespace(n=line_count)
        self.PQ = SimpleNamespace(n=2)
        self.PV = SimpleNamespace(n=3)
        self.Slack = SimpleNamespace(n=1)
        self.StaticGen = _FakeStaticGen()
        self.GENROU = _FakeModel(idx=range(1, 5), u=[1] * 4)
        self.TGOV1 = _FakeModel(idx=range(1, 5), u=[1] * 4, syn=range(1, 5))
        self.EXDC2 = _FakeModel(idx=range(1, 5), u=[1] * 4, syn=range(1, 5))
        self.models = {
            "GENROU": self.GENROU,
            "TGOV1": self.TGOV1,
            "EXDC2": self.EXDC2,
        }
        self.added = []

    def add(self, model, payload):
        self.added.append((model, dict(payload)))


def test_builder_replaces_each_dynamic_chain_with_one_regcv1() -> None:
    system = _FakeSystem()

    built = build_regcv1_kundur_object(system=system)

    assert [model for model, _ in system.added] == ["REGCV1"] * 4
    assert [payload for _, payload in system.added] == [
        {
            "idx": f"REGCV1_{index}",
            "bus": index,
            "gen": index,
            "Sn": 900.0,
            "fn": 60.0,
            "Tc": 0.01,
            "kw": 0.0,
            "kv": 0.01,
            "M": 10.0,
            "D": 0.0,
            "ra": 0.0,
            "xs": 0.2,
            "gammap": 1.0,
            "gammaq": 1.0,
        }
        for index in range(1, 5)
    ]
    assert all(value == 0 for value in system.GENROU.u.v)
    assert all(value == 0 for value in system.TGOV1.u.v)
    assert all(value == 0 for value in system.EXDC2.u.v)
    assert len(built.bindings) == 4
    assert len(built.disabled_dynamic_chain) == 12


def test_builder_refuses_network_inventory_drift() -> None:
    with pytest.raises(ValueError, match="network inventory"):
        build_regcv1_kundur_object(system=_FakeSystem(line_count=14))
