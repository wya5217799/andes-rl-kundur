from __future__ import annotations

import math

import numpy as np

from andes_rl_kundur.control.cascaded_washout import (
    CascadedHPDampingDistributedController,
)
from andes_rl_kundur.control.feasibility_native_deterministic import (
    HPDampingDistributedController,
)


ADJACENCY = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}


def _controller() -> CascadedHPDampingDistributedController:
    return CascadedHPDampingDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=4.0,
        ki_n_per_hz_s=0.8,
        ks_n_per_hz=1.0,
        kc_n_per_s=0.5,
        highpass_alpha=0.9391013674242926,
    )


def test_cascaded_controller_returns_zero_at_nominal_frequency() -> None:
    controller = _controller()
    action = controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    assert np.allclose(action, 0.0, atol=1.0e-12)


def test_cascaded_controller_reduces_ten_second_sustained_action_energy() -> None:
    candidate = CascadedHPDampingDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=0.0,
        ki_n_per_hz_s=0.0,
        ks_n_per_hz=1.0,
        kc_n_per_s=0.5,
        highpass_alpha=0.9391013674242926,
    )
    first_order = HPDampingDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=0.0,
        ki_n_per_hz_s=0.0,
        ks_n_per_hz=1.0,
        kc_n_per_s=0.5,
        highpass_alpha=0.90,
    )
    frequencies = [59.99, 59.99, 60.01, 60.01]
    candidate_actions = np.asarray(
        [candidate.act(frequencies_hz=frequencies, dt_seconds=0.2) for _ in range(50)]
    )
    first_order_actions = np.asarray(
        [
            first_order.act(frequencies_hz=frequencies, dt_seconds=0.2)
            for _ in range(50)
        ]
    )
    energy_ratio = float(
        np.sum(candidate_actions**2) / np.sum(first_order_actions**2)
    )
    assert energy_ratio <= 0.85


def test_cascaded_controller_passes_the_frozen_point_four_hz_mode() -> None:
    controller = CascadedHPDampingDistributedController(
        adjacency=ADJACENCY,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_n_per_hz=0.0,
        ki_n_per_hz_s=0.0,
        ks_n_per_hz=1.0,
        kc_n_per_s=0.5,
        highpass_alpha=0.9391013674242926,
    )
    time = np.arange(0.0, 80.0, 0.2)
    mode = np.array([1.0, 1.0, -1.0, -1.0])
    amplitude_hz = 0.001
    actions = np.asarray(
        [
            controller.act(
                frequencies_hz=(
                    60.0
                    + amplitude_hz
                    * math.sin(2.0 * math.pi * 0.4 * instant)
                    * mode
                ),
                dt_seconds=0.2,
            )
            for instant in time
        ]
    )
    steady = time >= 40.0
    input_message_rms = 2.0 * amplitude_hz / math.sqrt(2.0)
    output_rms = float(np.sqrt(np.mean(actions[steady, 0] ** 2)))
    assert output_rms / input_message_rms >= 0.90


def test_cascaded_controller_reset_clears_episode_state() -> None:
    controller = _controller()
    controller.act(
        frequencies_hz=[59.9, 59.9, 60.1, 60.1],
        dt_seconds=0.2,
    )
    controller.reset()
    action = controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    assert np.allclose(action, 0.0, atol=1.0e-12)


def test_cascaded_controller_keeps_actions_inside_the_frozen_clip() -> None:
    controller = _controller()
    for _ in range(50):
        action = controller.act(
            frequencies_hz=[55.0, 57.0, 63.0, 61.0],
            dt_seconds=0.2,
        )
    assert np.all(np.abs(action) <= 0.70 + 1.0e-12)
