"""Unit tests for the PPVSM1 two-unit builder (fake system loader)."""

from __future__ import annotations

from types import SimpleNamespace

from andes_rl_kundur.env.andes.ppvsm1_static_kundur import (
    build_ppvsm1_static_kundur_object,
)
from andes_rl_kundur.evaluation.ppvsm1_object_gate import (
    PPVSM1_PARAMETER_CARD,
    STATIC_MODELS,
)


def _full_case() -> dict:
    payload = {name: [{"idx": f"{name}_1", "u": 1.0}] for name in STATIC_MODELS}
    payload.update(
        {
            "GENROU": [{"idx": 1, "u": 1.0}],
            "TGOV1": [{"idx": 1, "u": 1.0}],
            "EXDC2": [{"idx": 1, "u": 1.0}],
            "Toggler": [{"idx": 1, "u": 1.0}],
        }
    )
    return payload


class _StaticGen:
    n = 4

    @staticmethod
    def get(*, src, idx, attr):
        assert attr == "v"
        if src == "bus":
            if idx == [1, 2]:
                return [1, 2]
            return [1, 2, 3, 4]
        if src == "Sn":
            if idx == [1, 2]:
                return [900.0, 900.0]
            return [900.0] * 4
        raise KeyError(src)


class _System:
    def __init__(self, *, retained_model: str | None = None):
        self.Bus = SimpleNamespace(n=10)
        self.Line = SimpleNamespace(n=15)
        self.PQ = SimpleNamespace(n=2)
        self.StaticGen = _StaticGen()
        for name in (
            "REGCV1",
            "REGCV2",
            "REGF1",
            "REGF2",
            "REGF3",
            "GENROU",
            "TGOV1",
            "EXDC2",
            "Toggler",
            "Toggle",
            "PLL1",
            "PLL2",
        ):
            setattr(self, name, SimpleNamespace(n=int(name == retained_model)))
        self.PPVSM1 = SimpleNamespace(n=0)
        self.added: list[tuple[str, dict]] = []

    def add(self, model, payload):
        self.added.append((model, dict(payload)))
        payload.pop("idx")


def test_builder_adds_two_ppvsm1_at_buses_1_2(tmp_path) -> None:
    system = _System()

    def loader(path):
        return system

    built = build_ppvsm1_static_kundur_object(
        full_case=_full_case(), work_dir=tmp_path, system_loader=loader
    )
    assert all(v == 0 for v in built.forbidden_model_counts.values())
    assert [row["idx"] for row in built.bindings] == ["PPVSM1_1", "PPVSM1_2"]
    assert [row["bus"] for row in built.bindings] == [1, 2]
    assert [row["gen"] for row in built.bindings] == [1, 2]
    assert all(row["Sn"] == 900.0 for row in built.bindings)
    assert all(
        row["mf"] == PPVSM1_PARAMETER_CARD["mf"] for row in built.bindings
    )
    assert [call[0] for call in system.added] == ["PPVSM1", "PPVSM1"]
    assert built.network_inventory == {
        "bus_count": 10,
        "line_count": 15,
        "pq_count": 2,
        "static_gen_count": 4,
        "static_generator_buses": [1, 2, 3, 4],
        "ppvsm1_buses": [1, 2],
        "static_anchor_buses": [3, 4],
    }


def test_builder_rejects_retained_dynamic_model(tmp_path) -> None:
    system = _System(retained_model="GENROU")

    def loader(path):
        return system

    try:
        build_ppvsm1_static_kundur_object(
            full_case=_full_case(), work_dir=tmp_path, system_loader=loader
        )
    except ValueError as exc:
        assert "structurally present" in str(exc)
    else:
        raise AssertionError("expected ValueError for retained dynamic model")


def test_builder_rejects_preexisting_ppvsm1(tmp_path) -> None:
    system = _System()
    system.PPVSM1 = SimpleNamespace(n=1)

    def loader(path):
        return system

    try:
        build_ppvsm1_static_kundur_object(
            full_case=_full_case(), work_dir=tmp_path, system_loader=loader
        )
    except ValueError as exc:
        assert "already exist" in str(exc)
    else:
        raise AssertionError("expected ValueError for preexisting PPVSM1")
