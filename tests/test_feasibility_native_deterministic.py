from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.feasibility_native_deterministic import (
    FeasibilityNativeDistributedController,
    FeasibilityNativeLocalController,
    HPDampingDistributedController,
    candidate_arm_ids,
    hp_damping_candidate_arm_ids,
)

ADJACENCY = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}


def test_local_zero_error_returns_zero_action() -> None:
    controller = FeasibilityNativeLocalController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
    )
    action = controller.act(frequencies_hz=[60.0, 60.0, 60.0, 60.0], dt_seconds=0.2)
    assert np.allclose(action, 0.0, atol=1e-12)


def test_local_positive_error_yields_positive_bounded_action() -> None:
    controller = FeasibilityNativeLocalController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
    )
    action = controller.act(
        frequencies_hz=[59.9, 59.9, 59.9, 59.9],
        dt_seconds=0.2,
    )
    assert np.all(action > 0.0)
    assert np.all(np.abs(action) <= 0.70 + 1e-12)


def test_local_action_stays_inside_frozen_clip() -> None:
    controller = FeasibilityNativeLocalController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
    )
    for _ in range(50):
        action = controller.act(
            frequencies_hz=[55.0, 55.0, 55.0, 55.0],
            dt_seconds=0.2,
        )
    assert np.all(np.abs(action) <= 0.70 + 1e-12)


def test_integrator_freezes_when_clipped() -> None:
    controller = FeasibilityNativeLocalController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
    )
    controller.act(frequencies_hz=[55.0] * 4, dt_seconds=0.2)
    integral_after_saturation = controller._integral.copy()
    controller.act(frequencies_hz=[55.0] * 4, dt_seconds=0.2)
    assert np.allclose(controller._integral, integral_after_saturation, atol=1e-12)


def test_local_rejects_bad_arguments() -> None:
    controller = FeasibilityNativeLocalController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
    )
    with pytest.raises(ValueError):
        controller.act(frequencies_hz=[60.0, 60.0, 60.0], dt_seconds=0.2)
    with pytest.raises(ValueError):
        controller.act(frequencies_hz=[float("nan")] * 4, dt_seconds=0.2)
    with pytest.raises(ValueError):
        controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.0)


def test_distributed_zero_error_returns_zero_action() -> None:
    controller = FeasibilityNativeDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
        ks_n_per_hz=0.5,
        kc_n_per_s=0.5,
    )
    action = controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    assert np.allclose(action, 0.0, atol=1e-12)


def test_distributed_differential_frequency_yields_zero_sum_component() -> None:
    controller = FeasibilityNativeDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
        ks_n_per_hz=0.5,
        kc_n_per_s=0.5,
    )
    action = controller.act(
        frequencies_hz=[59.9, 59.9, 60.1, 60.1],
        dt_seconds=0.2,
    )
    assert np.all(np.abs(action) <= 0.70 + 1e-12)


def test_distributed_bounded_under_large_frequency_error() -> None:
    controller = FeasibilityNativeDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
        ks_n_per_hz=1.0,
        kc_n_per_s=1.0,
    )
    for _ in range(50):
        action = controller.act(
            frequencies_hz=[55.0, 57.0, 63.0, 61.0],
            dt_seconds=0.2,
        )
    assert np.all(np.abs(action) <= 0.70 + 1e-12)


def test_distributed_rejects_bad_arguments() -> None:
    with pytest.raises(ValueError):
        FeasibilityNativeDistributedController(
            adjacency={0: [1], 1: [0], 2: [1], 3: [0]},
            device_count=4,
            nominal_frequency_hz=60.0,
            kp_n_per_hz=4.0,
            ki_n_per_hz_s=0.8,
            ks_n_per_hz=1.0,
            kc_n_per_s=1.0,
        )


def test_candidate_ids_frozen_grid() -> None:
    assert candidate_arm_ids() == [
        "distributed_feasibility_native_ks0p5_kc0p5",
        "distributed_feasibility_native_ks0p5_kc1",
        "distributed_feasibility_native_ks1_kc0p5",
        "distributed_feasibility_native_ks1_kc1",
    ]


def test_hp_candidate_ids_frozen_grid() -> None:
    assert hp_damping_candidate_arm_ids() == [
        "distributed_hp_damping_ks0p5_kc0p5_alpha0p6",
        "distributed_hp_damping_ks0p5_kc1_alpha0p6",
        "distributed_hp_damping_ks1_kc0p5_alpha0p6",
        "distributed_hp_damping_ks1_kc1_alpha0p6",
    ]


def _hp_controller(ks: float = 1.0, kc: float = 1.0, alpha: float = 0.60):
    return HPDampingDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
        ks_n_per_hz=ks,
        kc_n_per_s=kc,
        highpass_alpha=alpha,
    )


def test_hp_zero_error_returns_zero_action() -> None:
    controller = _hp_controller()
    action = controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    assert np.allclose(action, 0.0, atol=1e-12)


def test_hp_sustained_differential_is_attenuated() -> None:
    controller = _hp_controller(ks=1.0, kc=1.0, alpha=0.60)
    sustained = np.array([59.9, 59.9, 60.1, 60.1], dtype=float)
    controller.act(frequencies_hz=sustained, dt_seconds=0.2)
    controller.act(frequencies_hz=sustained, dt_seconds=0.2)
    highpass_state = controller._highpass_state
    assert np.all(np.abs(highpass_state) < np.abs(np.array([-0.2, -0.2, 0.2, 0.2])))


def test_hp_oscillatory_differential_passes_through() -> None:
    controller = _hp_controller(ks=1.0, kc=1.0, alpha=0.60)
    frequencies = [60.0, 60.0, 60.0, 60.0]
    controller.act(frequencies_hz=frequencies, dt_seconds=0.2)
    oscillating = [60.05, 60.05, 59.95, 59.95]
    controller.act(frequencies_hz=oscillating, dt_seconds=0.2)
    action = controller.act(frequencies_hz=oscillating, dt_seconds=0.2)
    assert np.max(np.abs(action)) > 0.0


def test_hp_action_bounded_inside_clip() -> None:
    controller = _hp_controller(ks=1.0, kc=1.0, alpha=0.60)
    for _ in range(50):
        action = controller.act(
            frequencies_hz=[55.0, 57.0, 63.0, 61.0],
            dt_seconds=0.2,
        )
    assert np.all(np.abs(action) <= 0.70 + 1e-12)


def test_hp_rejects_bad_alpha() -> None:
    with pytest.raises(ValueError):
        _hp_controller(alpha=1.0)
    with pytest.raises(ValueError):
        _hp_controller(alpha=0.0)


def test_hp_integrator_freezes_when_clipped() -> None:
    controller = _hp_controller(ks=1.0, kc=1.0, alpha=0.60)
    controller.act(frequencies_hz=[55.0] * 4, dt_seconds=0.2)
    integral_after_saturation = controller._integral.copy()
    controller.act(frequencies_hz=[55.0] * 4, dt_seconds=0.2)
    assert np.allclose(controller._integral, integral_after_saturation, atol=1e-12)
