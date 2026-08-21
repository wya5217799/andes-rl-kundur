"""Slice-10 tests: R408 solving-gate contract, arms, telemetry, decision tree."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.run_r408_v2_solving_gate import (
    BLEND_B1,
    BLEND_E1,
    K_GRID_STAGE_A,
    K_GRID_STAGE_B,
    bandpass_arm_id,
    build_contract,
    solving_decision,
)
from scripts.run_r408_v2_solving_gate import _bandpass_k_from_arm_id


def test_arm_id_round_trip():
    for k in (*K_GRID_STAGE_A, *K_GRID_STAGE_B):
        arm = bandpass_arm_id(k)
        assert _bandpass_k_from_arm_id(arm) == pytest.approx(k, rel=1e-12)
    assert bandpass_arm_id(0.0) == "bandpass_k0"
    assert bandpass_arm_id(0.001) == "bandpass_k0p001"
    assert bandpass_arm_id(0.075) == "bandpass_k0p075"
    assert bandpass_arm_id(2.25) == "bandpass_k2p25"
    assert bandpass_arm_id(3.5) == "bandpass_k3p5"


def test_contract_freeze_per_arm():
    c = build_contract("bandpass_k3p5")
    assert c["round"] == "R408"
    assert c["development"]["arm_ids"] == [
        "zero_feedback",
        "local_feasibility_native",
        "bandpass_k3p5",
    ]
    assert c["development"]["record_count"] == 3 * (8 + 2)
    assert c["training_authorized"] is False
    c2 = build_contract(BLEND_B1)
    assert c2["development"]["arm_ids"][-1] == BLEND_B1


def test_decision_tree():
    failing = [
        {"arm_id": "bandpass_k2p25", "passed": False},
        {"arm_id": "blend_b1", "passed": False},
    ]
    d = solving_decision(failing)
    assert d["classification"] == "SEARCHED-FAMILIES-NEGATIVE"
    assert d["found_candidate"] is None
    passing = [
        {"arm_id": "bandpass_k2p25", "passed": False},
        {
            "arm_id": "blend_b1",
            "passed": True,
            "differential_ratio": 0.94,
            "probe_cross_ratio": 0.99,
            "strict_cross_pass": False,
        },
    ]
    d2 = solving_decision(passing)
    assert d2["classification"] == "Q-ENTRY"
    assert d2["found_candidate"]["arm_id"] == "blend_b1"


def test_telemetry_enrich_row():
    from types import SimpleNamespace

    from scripts.run_r408_v2_solving_gate import REQUIRED_ROW_KEYS, _enrich_row

    mapped = SimpleNamespace(
        lower_power_system_pu=np.zeros(4),
        upper_power_system_pu=np.ones(4),
        zero_anchor_power_system_pu=np.full(4, 0.5),
        feasible_power_system_pu=np.full(4, 0.5),
    )
    row = _enrich_row(
        {
            "commanded_power_system_pu": [0.5] * 4,
            "requested_power_system_pu": [0.5] * 4,
        },
        normalized=np.zeros(4),
        controller_action=np.zeros(4),
        common_action=np.zeros(4),
        differential_action=np.zeros(4),
        mapped=mapped,
    )
    for key in REQUIRED_ROW_KEYS:
        assert key in row, f"missing estimator-required key {key}"
    telemetry = row["zero_sum_telemetry"]
    assert set(telemetry) == {"sigma_v", "sigma_p", "sigma_distortion"}
    assert telemetry["sigma_v"] == 0.0
    assert telemetry["sigma_p"] == 0.0
    assert telemetry["sigma_distortion"] == 0.0


def test_controller_factory():
    from scripts.run_r408_v2_solving_gate import _make_controller

    contract = build_contract("bandpass_k0")
    ctrl = _make_controller("bandpass_k0", contract)
    assert ctrl is not None
    out = ctrl.act(np.array([60.02, 59.98, 60.01, 59.99]), dt_seconds=0.2)
    # gain 0: exactly zero command
    assert np.all(np.abs(out) < 1e-12)

    for arm_id in (BLEND_B1, BLEND_E1):
        ctrl = _make_controller(arm_id, build_contract(arm_id))
        omega = np.array([60.02, 59.98, 60.01, 59.99])
        out = ctrl.act(frequencies_hz=omega, dt_seconds=0.2)
        assert out.shape == (4,)
        assert np.all(np.abs(out) <= 0.70 + 1e-12)

    assert _make_controller("zero_feedback", contract) is None


def test_blend_sub_controller_frozen_parameters():
    from scripts.run_r408_v2_solving_gate import (
        BLEND_A_ALPHA,
        BLEND_B_K,
        _blend_sub_controllers,
    )

    a_law, b_law = _blend_sub_controllers(build_contract(BLEND_B1))
    assert a_law.alpha == BLEND_A_ALPHA == 0.85
    assert b_law._bandpass.gain == BLEND_B_K == 2.0
