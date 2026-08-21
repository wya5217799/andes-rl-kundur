"""Runner tests for the R392 loop-perturbation gate.

Import the runner module through the R391 parent chain (no ANDES execution)
and lock the perturbation-injection seam with a fake REGF2 model.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_runner():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/run_r392_regf2_loop_perturbation_gate.py"
    )
    spec = importlib.util.spec_from_file_location("r392_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeRegf2:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.values: dict[tuple[str, int], float] = {}

    def set(self, src: str, idx, value, base=None) -> None:
        self.calls.append((src, idx, value, base))
        self.values[(src, idx)] = float(value)

    def get(self, src: str, idx, attr: str = "v"):
        return self.values[(src, idx)]


class _FakeSystem:
    def __init__(self) -> None:
        self.REGF2 = _FakeRegf2()


def test_contract_preserves_r391_science() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    assert contract["object_contract"]["andes_version"] == "2.0.0"
    assert contract["object_contract"]["device_rating_mva"] == 900.0
    assert set(contract["registered_state_variables"]) == {"REGF2", "PLL2"}
    assert len(contract["arms"]) == 8


def test_apply_perturbation_none_is_inert() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    system = _FakeSystem()
    arm_spec = {"name": "A0_reference", "tds_tolerance": 1e-4, "perturbation": None}
    result = module._apply_perturbation(system, arm_spec, contract)
    assert result["applied"] is False
    assert result["readback"] == []
    assert system.REGF2.calls == []


def test_apply_perturbation_sets_all_four_devices_with_device_base() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    system = _FakeSystem()
    arm_spec = {
        "name": "H1a_mf_x4",
        "tds_tolerance": 1e-4,
        "perturbation": {"param": "mf", "factor": 4.0},
    }
    result = module._apply_perturbation(system, arm_spec, contract)
    assert result["expected_value"] == 0.6
    assert result["readback"] == [0.6, 0.6, 0.6, 0.6]
    assert result["applied"] is True
    assert system.REGF2.calls == [
        ("mf", device_id, 0.6, "device")
        for device_id in ("REGF2_1", "REGF2_2", "REGF2_3", "REGF2_4")
    ]


def test_apply_perturbation_absolute_value() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    system = _FakeSystem()
    arm_spec = {
        "name": "H4_Sn_100",
        "tds_tolerance": 1e-4,
        "perturbation": {"param": "Sn", "value": 100.0},
    }
    result = module._apply_perturbation(system, arm_spec, contract)
    assert result["expected_value"] == 100.0
    assert result["readback"] == [100.0] * 4


def test_apply_perturbation_unknown_param_raises() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    system = _FakeSystem()
    arm_spec = {
        "name": "bad",
        "tds_tolerance": 1e-4,
        "perturbation": {"param": "not_a_param", "factor": 2.0},
    }
    with pytest.raises(RuntimeError):
        module._apply_perturbation(system, arm_spec, contract)


def test_empty_arm_carries_perturbation_record() -> None:
    module = _load_runner()
    contract = module.build_regf2_loop_perturbation_contract()
    arm_spec = contract["arms"][0]
    record = module._empty_arm(arm_spec, contract)
    assert record["name"] == "A0_reference"
    assert record["perturbation"] == {
        "param": None,
        "factor": None,
        "expected_value": None,
        "readback": [],
        "applied": False,
    }
    assert record["trajectory_count"] == 0
