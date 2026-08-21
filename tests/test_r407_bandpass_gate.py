"""Slice-10 tests: B-round bandpass gate contract, adapter, and decision tree."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.run_r407_bandpass_gate import (
    K_GRID,
    bandpass_arm_controller,
    bandpass_arm_id,
    bandpass_decision,
    build_contract,
)

NOMINAL_HZ = 60.0


def test_contract_freezes_bandpass_structure():
    c = build_contract()
    assert c["bandpass"] == {
        "f0_hz": 0.4,
        "zeta": 0.35,
        "controller_action_clip": 0.70,
    }
    assert c["k_grid"] == [0.10, 0.25, 0.50, 1.00, 2.00]
    from scripts.run_r407_bandpass_gate import k_contract
    assert k_contract(0.5)["development"]["arm_ids"] == [
        "zero_feedback",
        "local_feasibility_native",
        "bandpass_k0p5",
    ]
    assert c["training_authorized"] is False


def test_bandpass_controller_zero_sum_and_clip():
    ctrl = bandpass_arm_controller(bandpass_arm_id(0.5), contract=build_contract())
    # Constant differential input decays to zero (DC gain 0); the command must
    # always stay zero-sum and inside the clip.
    omega = np.array([60.02, 59.98, 60.01, 59.99])
    for _ in range(100):
        action = ctrl.act(omega, dt_seconds=0.2)
        assert action.shape == (4,)
        assert abs(float(np.sum(action))) < 1e-9
        assert np.all(np.abs(action) <= 0.70 + 1e-12)
    assert np.all(np.abs(action) < 1e-6)


def test_bandpass_controller_common_input_is_zero():
    ctrl = bandpass_arm_controller(bandpass_arm_id(1.0), contract=build_contract())
    omega = np.full(4, 60.03)
    for _ in range(30):
        action = ctrl.act(omega, dt_seconds=0.2)
    assert np.all(np.abs(action) < 1e-9)


def test_bandpass_decision_found_and_fail():
    grid = [
        {"k": 0.10, "any_pass": False, "arm_results": []},
        {"k": 0.25, "any_pass": True,
         "arm_results": [{"arm_id": "bandpass_k0p25", "passed": True}]},
        {"k": 0.50, "any_pass": True,
         "arm_results": [{"arm_id": "bandpass_k0p5", "passed": True}]},
    ]
    d = bandpass_decision(grid)
    assert d["classification"] == "BAND-PASS"
    assert d["found_candidate"] == {"k": 0.25, "arm_id": "bandpass_k0p25"}
    d2 = bandpass_decision(
        [{"k": k, "any_pass": False, "arm_results": []} for k in K_GRID]
    )
    assert d2["classification"] == "BAND-FAIL"
    assert d2["found_candidate"] is None


def test_k_grid_is_frozen():
    assert K_GRID == (0.10, 0.25, 0.50, 1.00, 2.00)


def test_enrich_row_produces_all_estimator_required_keys():
    # R407-pre-repair-3 regression: the forked job loop must attach every
    # estimator-required row field or every record fails the guard check.
    from types import SimpleNamespace

    import numpy as np

    from scripts.run_r407_bandpass_gate import REQUIRED_ROW_KEYS, _enrich_row

    mapped = SimpleNamespace(
        lower_power_system_pu=np.zeros(4),
        upper_power_system_pu=np.ones(4),
        zero_anchor_power_system_pu=np.full(4, 0.5),
        feasible_power_system_pu=np.full(4, 0.5),
    )
    row = _enrich_row(
        {},
        normalized=np.zeros(4),
        controller_action=np.zeros(4),
        common_action=np.zeros(4),
        differential_action=np.zeros(4),
        mapped=mapped,
    )
    for key in REQUIRED_ROW_KEYS:
        assert key in row, f"missing estimator-required key {key}"
    assert len(row["bound_contact"]) == 4


def test_controller_factory_recognizes_bandpass_arms():
    from scripts.run_r407_bandpass_gate import _make_controller, k_contract
    ctrl = _make_controller(bandpass_arm_id(0.5), k_contract(0.5))
    assert isinstance(ctrl, type(bandpass_arm_controller(
        bandpass_arm_id(0.5), contract=k_contract(0.5))))
    assert _make_controller("zero_feedback", k_contract(0.5)) is None