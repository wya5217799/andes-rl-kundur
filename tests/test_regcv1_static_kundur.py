from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from andes_rl_kundur.env.andes.regcv1_static_kundur import (
    STATIC_MODELS,
    build_regcv1_static_kundur_object,
    load_verified_static_case,
    render_static_case_bytes,
)


def _full_case() -> dict:
    payload = {
        name: [{"idx": f"{name}_1", "u": 1.0}]
        for name in STATIC_MODELS
    }
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
    def __init__(self, *, legacy_count: int = 0):
        self.Bus = SimpleNamespace(n=10)
        self.Line = SimpleNamespace(n=15)
        self.PQ = SimpleNamespace(n=2)
        self.StaticGen = _StaticGen()
        self.REGCV1 = SimpleNamespace(n=0)
        self.GENROU = SimpleNamespace(n=legacy_count)
        self.TGOV1 = SimpleNamespace(n=legacy_count)
        self.EXDC2 = SimpleNamespace(n=legacy_count)
        self.Toggler = SimpleNamespace(n=legacy_count)
        self.added: list[tuple[str, dict]] = []

    def add(self, model, payload):
        self.added.append((model, dict(payload)))


def test_static_case_bytes_are_deterministic_and_exclude_dynamic_records() -> None:
    rendered = render_static_case_bytes(_full_case())
    decoded = json.loads(rendered)

    assert tuple(decoded) == STATIC_MODELS
    assert render_static_case_bytes(_full_case()) == rendered
    assert not {"GENROU", "TGOV1", "EXDC2", "Toggler"} & decoded.keys()


def test_builder_loads_structurally_static_case_and_adds_four_regcv1(tmp_path) -> None:
    observed: dict = {}

    def loader(path):
        observed.update(json.loads(path.read_text(encoding="utf-8")))
        return _System()

    built = build_regcv1_static_kundur_object(
        full_case=_full_case(),
        work_dir=tmp_path,
        system_loader=loader,
    )

    assert tuple(observed) == STATIC_MODELS
    assert len(built.bindings) == 4
    assert [model for model, _ in built.system.added] == ["REGCV1"] * 4
    assert built.forbidden_model_counts == {
        "GENROU": 0,
        "TGOV1": 0,
        "EXDC2": 0,
        "Toggler": 0,
    }
    assert len(built.derived_case_sha256) == 64


def test_builder_refuses_any_retained_legacy_model(tmp_path) -> None:
    with pytest.raises(ValueError, match="legacy models are structurally present"):
        build_regcv1_static_kundur_object(
            full_case=_full_case(),
            work_dir=tmp_path,
            system_loader=lambda _path: _System(legacy_count=1),
        )


def test_packaged_source_audit_requires_full_xlsx_json_static_equality(tmp_path) -> None:
    full_case = _full_case()
    workbook = Workbook()
    workbook.remove(workbook.active)
    for model in STATIC_MODELS:
        sheet = workbook.create_sheet(model)
        sheet.append(["uid", "idx", "u"])
        row = full_case[model][0]
        sheet.append([0, row["idx"], row["u"]])
    xlsx_path = tmp_path / "case.xlsx"
    json_path = tmp_path / "case.json"
    workbook.save(xlsx_path)
    json_path.write_text(json.dumps(full_case), encoding="utf-8")

    audit = load_verified_static_case(xlsx_path=xlsx_path, json_path=json_path)

    assert audit.xlsx_json_static_equal is True
    assert audit.full_case == full_case
    assert len(audit.xlsx_sha256) == len(audit.json_sha256) == 64

    full_case["Bus"][0]["u"] = 0.0
    json_path.write_text(json.dumps(full_case), encoding="utf-8")
    with pytest.raises(ValueError, match="static table mismatch"):
        load_verified_static_case(xlsx_path=xlsx_path, json_path=json_path)
