"""Runner tests for the R397 PPVSM1 signed-authority bank."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r397_ppvsm1_signed_authority_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r397_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakePpvsm1:
    def __init__(self) -> None:
        self.idx = SimpleNamespace(v=["PPVSM1_1", "PPVSM1_2"])
        self.Pref = SimpleNamespace(v=np.asarray([0.5, 0.4], dtype=float))
        self.Qref = SimpleNamespace(v=np.asarray([0.1, 0.08], dtype=float))


class _FakeSystem:
    def __init__(self) -> None:
        self.PPVSM1 = _FakePpvsm1()


def test_contract_is_strictly_canonical() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    assert contract["round"] == "R397"
    assert contract["question"] == "Q-0111"
    assert contract["trajectory_count"] == 9
    assert len(contract["arm_order"]) == 9
    assert module.build_r397_contract() == module.build_ppvsm1_signed_authority_contract()


def test_frozen_parent_hashes_match_disk() -> None:
    module = _load_runner()
    parents = module.parent_manifest()
    assert {
        name: row["sha256"] for name, row in parents.items()
    } == module.R396_PARENT_SHA256


def test_parent_chain_validation_passes() -> None:
    module = _load_runner()
    assert module.validate_r396_parent_chain() is True


def test_parent_chain_validation_rejects_tampered_hashes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner()
    tampered = dict(module.R396_PARENT_SHA256)
    tampered["r396_seal"] = "0" * 64
    monkeypatch.setattr(module, "R396_PARENT_SHA256", tampered)
    assert module.validate_r396_parent_chain() is False


def test_setpoint_rows_order_matches_contract() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    system = _FakeSystem()
    rows = module._setpoint_rows(system, contract)
    assert [(row["idx"], row["channel"]) for row in rows] == [
        ("PPVSM1_1", "pref"),
        ("PPVSM1_1", "qref"),
        ("PPVSM1_2", "pref"),
        ("PPVSM1_2", "qref"),
    ]
    assert [row["value"] for row in rows] == [0.5, 0.1, 0.4, 0.08]


def test_setpoint_step_writes_only_the_target_channel() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    system = _FakeSystem()
    arm = contract["arm_order"][1]  # ppvsm1_1_pref_negative

    action = module.apply_ppvsm1_setpoint_step(system, arm, contract)

    assert action["applied"] is True
    assert action["requested_absolute"] == pytest.approx(0.5 - 0.09)
    assert action["applied_readback"] == pytest.approx(0.5 - 0.09)
    post = {
        (row["idx"], row["channel"]): row["value"] for row in action["post_setpoints"]
    }
    assert post[("PPVSM1_1", "pref")] == pytest.approx(0.41)
    assert post[("PPVSM1_1", "qref")] == pytest.approx(0.1)
    assert post[("PPVSM1_2", "pref")] == pytest.approx(0.4)
    assert post[("PPVSM1_2", "qref")] == pytest.approx(0.08)


def test_setpoint_step_positive_sign_and_qref_channel() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    system = _FakeSystem()
    arm = contract["arm_order"][4]  # ppvsm1_1_qref_positive

    action = module.apply_ppvsm1_setpoint_step(system, arm, contract)

    assert action["requested_absolute"] == pytest.approx(0.1 + 0.09)
    post = {
        (row["idx"], row["channel"]): row["value"] for row in action["post_setpoints"]
    }
    assert post[("PPVSM1_1", "qref")] == pytest.approx(0.19)
    assert post[("PPVSM1_1", "pref")] == pytest.approx(0.5)


def test_zero_arm_receipt_has_no_write() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    system = _FakeSystem()
    arm = contract["arm_order"][0]

    action = module.apply_ppvsm1_setpoint_step(system, arm, contract)

    assert action["applied"] is False
    assert action["requested_absolute"] is None
    assert action["applied_readback"] is None
    assert action["pre_setpoints"] == action["post_setpoints"]


def test_bus_major_conversion() -> None:
    module = _load_runner()
    converted = module._bus_major(
        [{"1": 1.0, "2": 1.1}, {"1": 1.2, "2": 1.3}]
    )
    assert converted == {"1": [1.0, 1.2], "2": [1.1, 1.3]}


def test_empty_arm_matches_classifier_shape() -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    arm = module._empty_arm(contract["arm_order"][2])
    assert arm["scientific_error"] is None
    assert arm["trajectory"]["captured"] is False
    assert arm["trajectory"]["initial"]["captured"] is False
    assert arm["trajectory"]["initial"]["devices"] == {}
    assert arm["solver"]["terminal_time_seconds"] is None


def test_execution_error_is_contained_and_classifies_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner()
    contract = module.build_r397_contract()
    runtime = {
        "andes_version": "2.0.0",
        "xlsx_json_static_equal": True,
        "xlsx_case_sha256": module.FROZEN_XLSX_SHA256,
        "json_case_sha256": module.FROZEN_JSON_SHA256,
        "derived_case_sha256": module.FROZEN_DERIVED_SHA256,
        "ppvsm1_model_sha256": module.FROZEN_PPVSM1_MODEL_SHA256,
        "xlsx_case_path": "unused.xlsx",
        "json_case_path": "unused.json",
    }

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        module.base,
        "load_verified_static_case",
        lambda **kwargs: SimpleNamespace(full_case={}),
    )
    monkeypatch.setattr(module, "build_ppvsm1_static_kundur_object", _boom)
    record = module.run_formal_record(contract, runtime)
    analysis = module.classify_ppvsm1_signed_authority_record(
        record, contract=contract
    )

    assert record["execution_error"] == "RuntimeError: boom"
    assert record["arms"] == []
    assert analysis["classification"] == "ANALYSIS-INVALID"


def test_rehearse_rejects_parent_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_runner()
    monkeypatch.setattr(module.base, "assert_wsl_scratch", lambda: None)
    monkeypatch.setattr(module, "validate_r396_parent_chain", lambda: False)
    with pytest.raises(RuntimeError, match="parent chain"):
        module.rehearse()


def test_rehearse_is_create_only(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _load_runner()
    monkeypatch.setattr(module.base, "assert_wsl_scratch", lambda: None)
    monkeypatch.setattr(module, "validate_r396_parent_chain", lambda: True)
    monkeypatch.setattr(
        module,
        "REHEARSAL",
        module.ROOT / "memory/rounds/R397/rehearsal.json",
    )
    collision = tmp_path / "rehearsal.json"
    collision.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "REHEARSAL", collision)
    with pytest.raises(FileExistsError, match="pre-attempt artifact"):
        module.rehearse()


def test_plan_and_question_reflect_the_closed_round() -> None:
    module = _load_runner()
    plan_text = module.PLAN.read_text(encoding="utf-8")
    question_text = module.QUESTION.read_text(encoding="utf-8")
    assert "state: completed" in plan_text
    assert "manuscript_line: converter-vsg-pq-decoupling" in plan_text
    assert "status: closed-negative" in question_text
    assert "closed_by: CLM-1130" in question_text
