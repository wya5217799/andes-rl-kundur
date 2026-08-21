"""Regression tests for the R402 slew-representation repair.

The frozen canary contract requires the recorded per-step normalized action
delta to stay within the slew limit (0.25) with a 1e-9 tolerance.  The R402
canary evaluation exposed a float32 rounding defect: a step clipped exactly
at the slew bound could be stored one float32 ulp outside it.  These tests
lock the repaired projector so every stored delta respects the exact bound.
"""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.per_vsg_md import (
    LocalMDActionProjector,
    PerVSGMDActionProjector,
)

SLEW = 0.25
TOLERANCE = 1.0e-9


def test_adversarial_random_walk_never_overshoots():
    rng = np.random.default_rng(402)
    projector = LocalMDActionProjector(action_slew_limit=SLEW)
    previous = np.zeros(2, dtype=np.float32)
    for _ in range(20000):
        target = rng.uniform(-1.2, 1.2, size=2).astype(np.float32)
        action = projector.project(target)
        delta = action.astype(np.float64) - previous.astype(np.float64)
        assert np.all(delta <= SLEW + TOLERANCE), (previous, action, delta)
        assert np.all(delta >= -SLEW - TOLERANCE), (previous, action, delta)
        assert np.all(action >= -1.0) and np.all(action <= 1.0)
        previous = action


def test_bang_bang_targets_at_bounds_stay_exact():
    projector = LocalMDActionProjector(action_slew_limit=SLEW)
    previous = np.zeros(2, dtype=np.float32)
    for _ in range(50):
        action = projector.project(np.array([1.0, -1.0], dtype=np.float32))
        delta = action.astype(np.float64) - previous.astype(np.float64)
        assert np.all(delta <= SLEW + TOLERANCE)
        assert np.all(delta >= -SLEW - TOLERANCE)
        previous = action
    assert np.allclose(action, [1.0, -1.0], atol=SLEW + 1e-6)


def test_four_row_projector_inherits_repair():
    rng = np.random.default_rng(403)
    projector = PerVSGMDActionProjector(action_slew_limit=SLEW)
    previous = np.zeros((4, 2), dtype=np.float32)
    for _ in range(5000):
        target = rng.uniform(-1.2, 1.2, size=(4, 2)).astype(np.float32)
        action = projector.project(target)
        delta = action.astype(np.float64) - previous.astype(np.float64)
        assert np.all(delta <= SLEW + TOLERANCE)
        assert np.all(delta >= -SLEW - TOLERANCE)
        previous = action


def test_reproduces_exact_case_from_canary_bank():
    projector = LocalMDActionProjector(action_slew_limit=SLEW)
    previous = np.array([-0.028620943427085876, 0.0], dtype=np.float32)
    projector.previous_action = previous
    action = projector.project(np.array([-1.0, 0.0], dtype=np.float32))
    delta = action.astype(np.float64) - previous.astype(np.float64)
    assert np.all(delta <= SLEW + TOLERANCE), (previous, action, delta)

