from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from andes_rl_kundur.env.andes.regf2_static_kundur import (
    REGF2_PARAMETER_CARD,
    build_regf2_static_kundur_object,
)
from andes_rl_kundur.evaluation.regf2_object_init_gate import STATIC_MODELS


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
        assert idx == [1, 2, 3, 4]
        assert attr == "v"
        if src == "bus":
            return [1, 2, 3, 4]
        if src == "Sn":
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
        ):
            setattr(self, name, SimpleNamespace(n=int(name == retained_model)))
        self.added: list[tuple[str, dict]] = []

    def add(self, model, payload):
        self.added.append((model, dict(payload)))
        payload.pop("idx")


def test_builder_adds_exact_four_stock_regf2_cards_to_static_kundur(tmp_path) -> None:
    observed: dict = {}

    def loader(path):
        observed.update(json.loads(path.read_text(encoding="utf-8")))
        return _System()

    built = build_regf2_static_kundur_object(
        full_case=_full_case(),
        work_dir=tmp_path,
        system_loader=loader,
    )

    assert tuple(observed) == STATIC_MODELS
    assert [model for model, _ in built.system.added] == ["REGF2"] * 4
    assert [row["idx"] for row in built.bindings] == [
        "REGF2_1",
        "REGF2_2",
        "REGF2_3",
        "REGF2_4",
    ]
    assert [row["bus"] for row in built.bindings] == [1, 2, 3, 4]
    assert all(row["Sn"] == 900.0 for row in built.bindings)
    assert all(
        all(row[key] == value for key, value in REGF2_PARAMETER_CARD.items())
        for row in built.bindings
    )
    assert built.forbidden_model_counts == {
        "REGCV1": 0,
        "REGCV2": 0,
        "REGF1": 0,
        "REGF3": 0,
        "GENROU": 0,
        "TGOV1": 0,
        "EXDC2": 0,
        "Toggler": 0,
        "Toggle": 0,
    }
    assert len(built.derived_case_sha256) == 64


def test_builder_refuses_retained_or_preexisting_dynamic_object(tmp_path) -> None:
    for retained in ("GENROU", "REGCV1", "REGF2"):
        with pytest.raises(ValueError, match="structurally present|already exist"):
            build_regf2_static_kundur_object(
                full_case=_full_case(),
                work_dir=tmp_path / retained,
                system_loader=lambda _path, retained=retained: _System(
                    retained_model=retained
                ),
            )


def test_parameter_card_is_the_independent_installed_default_literal() -> None:
    assert REGF2_PARAMETER_CARD == {
        "rf": 0.0,
        "xf": 0.2,
        "Vdip": 0.8,
        "Tfrz": 0.0,
        "PQFLAG": 1.0,
        "fn": 60.0,
        "dwmax": 75.0,
        "dwmin": -75.0,
        "wdrp": 0.033,
        "Qdrp": 0.045,
        "Tr": 0.005,
        "Te": 0.005,
        "KPi": 0.5,
        "KIi": 20.0,
        "KPv": 3.0,
        "KIv": 10.0,
        "Pmax": 1.0,
        "Pmin": -1.0,
        "KPplim": 5.0,
        "KIplim": 30.0,
        "Qmax": 1.0,
        "Qmin": -1.0,
        "KPqlim": 0.1,
        "KIqlim": 1.5,
        "Tpm": 0.025,
        "gammap": 1.0,
        "gammaq": 1.0,
        "mf": 0.15,
        "dd": 0.11,
        "pll": None,
    }
