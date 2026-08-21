"""Slice-10 tests: R408 blend controllers (B1 fixed, E1 time-varying)."""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.blend_damping import (
    ACTION_CLIP,
    B1_B_WEIGHT,
    FADE_END_S,
    FADE_START_S,
    FixedBlendController,
    TimeVaryingBlendController,
)


class _ConstLaw:
    """Test double: returns one fixed action vector."""

    def __init__(self, value: np.ndarray) -> None:
        self._value = np.asarray(value, dtype=float)
        self.calls = 0

    def act(self, *, frequencies_hz: np.ndarray, dt_seconds: float) -> np.ndarray:
        self.calls += 1
        return self._value.copy()


def test_b1_mixes_before_clip():
    a = _ConstLaw(np.array([0.6, -0.6, 0.0, 0.0]))
    b = _ConstLaw(np.array([0.2, 0.2, -0.2, -0.2]))
    ctrl = FixedBlendController(a_controller=a, b_controller=b)
    out = ctrl.act(frequencies_hz=np.zeros(4), dt_seconds=0.2)
    expected = np.clip(
        np.array([0.6, -0.6, 0.0, 0.0]) + B1_B_WEIGHT * np.array([0.2, 0.2, -0.2, -0.2]),
        -ACTION_CLIP,
        ACTION_CLIP,
    )
    assert np.allclose(out, expected)
    assert a.calls == 1 and b.calls == 1


def test_b1_clips_the_sum():
    a = _ConstLaw(np.full(4, 0.6))
    b = _ConstLaw(np.full(4, 0.6))
    ctrl = FixedBlendController(a_controller=a, b_controller=b)
    out = ctrl.act(frequencies_hz=np.zeros(4), dt_seconds=0.2)
    assert np.all(np.abs(out) <= ACTION_CLIP + 1e-12)
    assert np.allclose(out, ACTION_CLIP)


def test_e1_gate_profile():
    a = _ConstLaw(np.ones(4))
    b = _ConstLaw(-np.ones(4))
    ctrl = TimeVaryingBlendController(a_controller=a, b_controller=b)
    # t = 3.0 s -> gate 1 -> A only (clipped to the action bound).
    for _ in range(15):
        out = ctrl.act(frequencies_hz=np.zeros(4), dt_seconds=0.2)
    assert np.allclose(out, ACTION_CLIP)
    # t = 3.6 -> fade start (15 steps = 3.0 s; 3 more = 3.6 s).
    out = ctrl.act(frequencies_hz=np.zeros(4), dt_seconds=0.2)
    assert np.isclose(ctrl._gate(), 1.0)
    # t >= 4.0 -> gate 0 -> B only (clipped to the action bound).
    for _ in range(5):
        out = ctrl.act(frequencies_hz=np.zeros(4), dt_seconds=0.2)
    assert np.isclose(ctrl._gate(), 0.0)
    assert np.allclose(out, -ACTION_CLIP)
    # A/B both keep running through the fade (call counts keep increasing).
    assert a.calls == b.calls == 21


def test_e1_gate_midpoint_is_half():
    ctrl = TimeVaryingBlendController(
        a_controller=_ConstLaw(np.zeros(4)),
        b_controller=_ConstLaw(np.zeros(4)),
    )
    ctrl._elapsed = 3.8  # exact midpoint of the cosine fade
    assert np.isclose(ctrl._gate(), 0.5)


def test_frozen_constants():
    assert FADE_START_S == 3.6
    assert FADE_END_S == 4.0
    assert B1_B_WEIGHT == 0.70
    assert ACTION_CLIP == 0.70


def test_e1_rejects_bad_window():
    with pytest.raises(ValueError):
        TimeVaryingBlendController(
            a_controller=_ConstLaw(np.zeros(4)),
            b_controller=_ConstLaw(np.zeros(4)),
            fade_start_s=4.0,
            fade_end_s=3.0,
        )
