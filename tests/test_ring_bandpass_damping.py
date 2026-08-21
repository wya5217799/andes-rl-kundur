"""Slice-9 tests: pre-warped 0.4 Hz ring-edge bandpass damping controller.

Expected values come from the external solver's frozen structure and from
hand-derived common-mode transparency / DC-zero / peak-gain properties.
"""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.ring_bandpass_damping import (
    RingBandpassDamping,
    prewarped_bandpass_coefficients,
)

DT = 0.2
F0 = 0.4
ZETA = 0.35
N = 4


def test_prewarped_bandpass_dc_gain_is_zero():
    num, den = prewarped_bandpass_coefficients(f0_hz=F0, zeta=ZETA, dt=DT, gain=1.0)
    # A bandpass has a zero at s=0; the discrete equivalent at z=1 (DC) must
    # give zero gain regardless of the prewarping.
    gain_dc = float(np.sum(num) / np.sum(den))
    assert gain_dc == pytest.approx(0.0, abs=1e-9)


def test_prewarped_bandpass_peak_is_at_target_frequency():
    num, den = prewarped_bandpass_coefficients(f0_hz=F0, zeta=ZETA, dt=DT, gain=1.0)
    # The gain correction anchors the magnitude at the exact physical target
    # digital frequency wm*dt (not at the Tustin-warped frequency), so the
    # magnitude there must be exactly the requested gain.
    w_target = 2.0 * np.pi * F0 * DT
    z = np.exp(1j * w_target)
    h = np.polyval(num, z) / np.polyval(den, z)
    assert abs(abs(h) - 1.0) < 1e-9


def test_ring_controller_common_transparency():
    ctrl = RingBandpassDamping(n=N, dt=DT, f0_hz=F0, zeta=ZETA, gain=1.0)
    omega = np.array([0.02, 0.02, 0.02, 0.02])
    command = ctrl.step(omega)
    assert command.shape == (N,)
    assert abs(float(np.sum(command))) < 1e-12
    # After transients, a pure common input must keep producing zero.
    for _ in range(50):
        command = ctrl.step(omega)
    assert abs(float(np.sum(command))) < 1e-12


def test_ring_controller_differential_steering_signs():
    ctrl = RingBandpassDamping(n=N, dt=DT, f0_hz=F0, zeta=ZETA, gain=1.0)
    # First-step response: v = -gain_feedthrough * L_ring * omega with a
    # positive feedthrough, so the command opposes the ring-edge difference:
    # for omega = [0.01, -0.01, 0.005, -0.005], L_ring omega = [0.035,
    # -0.025, 0.02, -0.02] -> command[0] < 0 and command[1] > 0.
    omega = np.array([0.01, -0.01, 0.005, -0.005])
    command = ctrl.step(omega)
    assert command[0] < 0.0
    assert command[1] > 0.0
    assert command[2] < 0.0
    assert command[3] > 0.0
    assert abs(float(np.sum(command))) < 1e-12


def test_ring_controller_dc_differential_input_decays_to_zero():
    ctrl = RingBandpassDamping(n=N, dt=DT, f0_hz=F0, zeta=ZETA, gain=1.0)
    omega = np.array([0.01, -0.01, 0.005, -0.005])
    for _ in range(200):
        command = ctrl.step(omega)
    # A bandpass has zero DC gain, so a constant input must decay.
    assert np.all(np.abs(command) < 1e-6)


def test_ring_controller_reset_clears_state():
    ctrl = RingBandpassDamping(n=N, dt=DT, f0_hz=F0, zeta=ZETA, gain=1.0)
    omega = np.array([0.01, -0.01, 0.005, -0.005])
    for _ in range(30):
        ctrl.step(omega)
    ctrl.reset()
    omega_common = np.array([0.02, 0.02, 0.02, 0.02])
    command = ctrl.step(omega_common)
    assert abs(float(np.sum(command))) < 1e-12
