"""Slice-2 tests: candidate-A action schedule and frozen linear cross energy.

Expected values come from independent symmetry arguments and hand-derived
ramp arithmetic -- not from re-running the implementation formulas.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


from probes.homogenization_linearization import (  # noqa: E402
    REGISTERED_DIFFERENTIAL_TRANSFORM,
    homogenized_action_schedule,
    linear_cross_energy,
)

RING_L = np.array([
    [2.0, -1.0, 0.0, -1.0],
    [-1.0, 2.0, -1.0, 0.0],
    [0.0, -1.0, 2.0, -1.0],
    [-1.0, 0.0, -1.0, 2.0],
])

ONE_COMMON = np.full((30, 4), 0.01)
ONE_DIFF = np.tile(np.array([0.01, -0.01, 0.005, -0.005]), (30, 1))


# ---------------------------------------------------------------------------
# Registered differential transform contract
# ---------------------------------------------------------------------------


def test_registered_differential_transform_contract():
    td = REGISTERED_DIFFERENTIAL_TRANSFORM
    assert td.shape == (3, 4)
    # Rows live in 1^perp.
    assert np.allclose(td @ np.ones(4), np.zeros(3), atol=1e-12)
    # Rows are orthonormal (so energy numbers are basis-independent).
    assert np.allclose(td @ td.T, np.eye(3), atol=1e-12)


# ---------------------------------------------------------------------------
# Action schedule: slew ramp then hold
# ---------------------------------------------------------------------------


def test_action_schedule_ramp_and_hold_hand_values():
    targets = np.zeros((4, 2))
    targets[0, 0] = 0.64645
    targets[1, 1] = -0.39645
    schedule = homogenized_action_schedule(targets, steps=30, slew=0.25)
    assert schedule.shape == (30, 4, 2)
    # Hand ramp: 0.25, 0.5, 0.64645 then hold; -0.25, -0.39645 then hold.
    assert schedule[0, 0, 0] == pytest.approx(0.25, abs=1e-12)
    assert schedule[1, 0, 0] == pytest.approx(0.5, abs=1e-12)
    assert schedule[2, 0, 0] == pytest.approx(0.64645, abs=1e-12)
    for k in range(3, 30):
        assert schedule[k, 0, 0] == pytest.approx(0.64645, abs=1e-12)
    assert schedule[0, 1, 1] == pytest.approx(-0.25, abs=1e-12)
    assert schedule[1, 1, 1] == pytest.approx(-0.39645, abs=1e-12)
    for k in range(2, 30):
        assert schedule[k, 1, 1] == pytest.approx(-0.39645, abs=1e-12)
    # All other coordinates stay at zero.
    assert np.all(schedule[:, 0, 1] == 0.0)
    assert np.all(schedule[:, 1, 0] == 0.0)
    assert np.all(schedule[:, 2:, :] == 0.0)


def test_action_schedule_random_targets_respect_slew_and_box():
    rng = np.random.default_rng(405)
    for _ in range(100):
        targets = rng.uniform(-1.0, 1.0, size=(4, 2))
        schedule = homogenized_action_schedule(targets, steps=30, slew=0.25)
        diffs = np.abs(np.diff(schedule, axis=0))
        assert np.all(diffs <= 0.25 + 1e-9)
        assert np.all(schedule >= -1.0) and np.all(schedule <= 1.0)
        assert np.allclose(schedule[-1], targets, atol=1e-12)


# ---------------------------------------------------------------------------
# Frozen linear cross energy on the balanced four-ring network
# ---------------------------------------------------------------------------


def _probe_bank(magnitude: float) -> tuple[np.ndarray, np.ndarray]:
    common = np.full((30, 4), magnitude)
    differential = np.tile(
        np.array([magnitude, -magnitude, 0.5 * magnitude, -0.5 * magnitude]),
        (30, 1),
    )
    return common, differential


def test_cross_energy_zero_for_homogeneous_balanced_network():
    # Symmetry: with M=mI, D=dI and a balanced Laplacian, a common injection
    # excites only the common mode, so the differential output energy is
    # exactly zero -- and vice versa.  This holds for any m, d > 0.
    for m, d in [(1.0, 1.0), (200.0, 90.0), (500.0, 3.0)]:
        common, differential = _probe_bank(0.01)
        out = linear_cross_energy(
            RING_L, [m] * 4, [d] * 4, [common, -common], [differential, -differential]
        )
        assert out["E_d_from_c"] == pytest.approx(0.0, abs=1e-9)
        assert out["E_c_from_d"] == pytest.approx(0.0, abs=1e-9)
        assert out["E_cross"] == pytest.approx(0.0, abs=1e-9)


def test_cross_energy_positive_for_heterogeneous_m():
    # Heterogeneous inertia couples the common mode into the differential
    # subspace; a pure common probe must leak into z_d.
    common, differential = _probe_bank(0.01)
    out = linear_cross_energy(
        RING_L, [1.0, 2.0, 3.0, 4.0], [5.0] * 4, [common, -common],
        [differential, -differential],
    )
    assert out["E_d_from_c"] > 0.0
    assert out["E_cross"] > 0.0


def test_cross_energy_homogenization_removes_the_leak():
    # The same heterogeneous case, but with all units moved to the common
    # moment-matched (m*, d*): the leak must vanish (balanced network).
    common, differential = _probe_bank(0.01)
    hetero = linear_cross_energy(
        RING_L, [1.0, 2.0, 3.0, 4.0], [5.0] * 4, [common, -common],
        [differential, -differential],
    )
    homo = linear_cross_energy(
        RING_L, [3.0] * 4, [5.0] * 4, [common, -common],
        [differential, -differential],
    )
    assert hetero["E_cross"] > 0.0
    assert homo["E_cross"] == pytest.approx(0.0, abs=1e-9)