from __future__ import annotations

import math

import numpy as np
import pytest

from andes_rl_kundur.control.cascaded_washout import CascadedWashout


DT_SECONDS = 0.2
CORNER_HZ = 0.05
MODE_HZ = 0.4
ALPHA = math.exp(-2.0 * math.pi * CORNER_HZ * DT_SECONDS)


def _response(values: np.ndarray, *, alpha: float = ALPHA) -> np.ndarray:
    filter_ = CascadedWashout(device_count=1, alpha=alpha)
    return np.asarray([filter_.step([value])[0] for value in values])


def _steady_sine_gain(frequency_hz: float) -> float:
    time = np.arange(0.0, 80.0, DT_SECONDS)
    signal = np.sin(2.0 * math.pi * frequency_hz * time)
    response = _response(signal)
    steady = time >= 40.0
    return float(
        np.sqrt(np.mean(response[steady] ** 2))
        / np.sqrt(np.mean(signal[steady] ** 2))
    )


def test_cascaded_washout_passes_frozen_mode_gain_gate() -> None:
    assert _steady_sine_gain(MODE_HZ) >= 0.90


def test_cascaded_washout_reduces_ten_second_step_energy() -> None:
    candidate = _response(np.ones(50, dtype=float))

    first_order_state = 0.0
    previous = 0.0
    first_order = []
    for value in np.ones(50, dtype=float):
        first_order_state = 0.90 * (first_order_state + value - previous)
        previous = value
        first_order.append(first_order_state)

    candidate_energy = float(np.sum(candidate**2) * DT_SECONDS)
    baseline_energy = float(np.sum(np.asarray(first_order) ** 2) * DT_SECONDS)
    assert candidate_energy / baseline_energy <= 0.85


def test_cascaded_washout_rejects_a_sustained_input_asymptotically() -> None:
    response = _response(np.ones(300, dtype=float))
    assert abs(response[-1]) <= 1.0e-6


def test_cascaded_washout_reset_clears_both_filter_stages() -> None:
    filter_ = CascadedWashout(device_count=2, alpha=ALPHA)
    filter_.step([1.0, -1.0])
    filter_.reset()
    assert np.allclose(filter_.step([0.0, 0.0]), 0.0, atol=1.0e-12)


def test_cascaded_washout_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        CascadedWashout(device_count=0, alpha=ALPHA)
    with pytest.raises(ValueError):
        CascadedWashout(device_count=1, alpha=1.0)

    filter_ = CascadedWashout(device_count=2, alpha=ALPHA)
    with pytest.raises(ValueError):
        filter_.step([0.0])
    with pytest.raises(ValueError):
        filter_.step([0.0, float("nan")])
