"""Pre-warped 0.4 Hz ring-edge bandpass damping controller (candidate B).

Motivation
----------
The owner-approved candidate-B structure (route_decision_bandpass_b_2026-08-16.md)
is a second-order positive-real bandpass on the ring-edge frequency differences
of the four VSG units: F(s) = K * 2*zeta*wm*s / (s^2 + 2*zeta*wm*s + wm^2) with
wm = 2*pi*0.4 rad/s.  It is exactly transparent to arithmetic common frequency
because the ring incidence matrix annihilates the all-ones vector (1^T v = 0).
This module is pure DSP -- no ANDES dependency -- so it is fully testable on
the Windows host; the WSL runner maps its output onto the feasibility-native
energy ports.

Usage
-----
    ctrl = RingBandpassDamping(n=4, dt=0.2, f0_hz=0.4, zeta=0.35, gain=K)
    command = ctrl.step(omega_hz_deviations)  # shape (4,), zero-sum

Failure modes
-------------
- A non-finite or wrong-shaped input raises instead of silently steering.
- The bilinear realization is gain-corrected so the magnitude at the exact
  0.4 Hz digital frequency equals the requested gain; callers must not apply
  a second correction.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


def prewarped_bandpass_coefficients(
    *,
    f0_hz: float,
    zeta: float,
    dt: float,
    gain: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Bilinear numerator/denominator with gain correction at exactly f0_hz.

    The continuous prototype is gain * 2*zeta*wm*s / (s^2 + 2*zeta*wm*s + wm^2)
    with wm = 2*pi*f0_hz.  After the Tustin transform the magnitude at the
    digital frequency wm*dt is measured and the numerator is scaled so it
    equals the requested gain there (pre-warping at the target frequency).
    """
    if f0_hz <= 0.0 or zeta <= 0.0 or dt <= 0.0 or gain < 0.0:
        raise ValueError("f0_hz, zeta, dt must be positive and gain nonnegative")
    wm = 2.0 * np.pi * f0_hz
    num_c = [gain * 2.0 * zeta * wm, 0.0]
    den_c = [1.0, 2.0 * zeta * wm, wm * wm]

    # Tustin transform: s -> (2/dt) (z-1)/(z+1).
    t = 2.0 / dt
    b0 = num_c[0] * t
    b1 = 0.0
    b2 = -num_c[0] * t
    a0 = den_c[0] * t * t + den_c[1] * t + den_c[2]
    a1 = -2.0 * den_c[0] * t * t + 2.0 * den_c[2]
    a2 = den_c[0] * t * t - den_c[1] * t + den_c[2]
    num = np.array([b0 / a0, b1 / a0, b2 / a0], dtype=float)
    den = np.array([1.0, a1 / a0, a2 / a0], dtype=float)

    # Gain correction at the exact target digital frequency.
    z_target = np.exp(1j * wm * dt)
    magnitude = abs(np.polyval(num, z_target) / np.polyval(den, z_target))
    if magnitude > 0.0:
        num = num * (gain / magnitude) if gain > 0.0 else num * 0.0
    elif gain == 0.0:
        num = np.zeros_like(num)
    return num, den


def ring_incidence(n: int) -> np.ndarray:
    """Oriented incidence matrix B (n nodes, n edges) of the n-node ring."""
    if n < 3:
        raise ValueError("a ring requires at least three nodes")
    b = np.zeros((n, n), dtype=float)
    for edge in range(n):
        b[edge, edge] = 1.0
        b[(edge + 1) % n, edge] = -1.0
    return b


class RingBandpassDamping:
    """Edge-wise bandpass damping; the output is zero-sum by construction."""

    def __init__(
        self,
        *,
        n: int,
        dt: float,
        f0_hz: float,
        zeta: float,
        gain: float,
    ) -> None:
        self.n = int(n)
        self.dt = float(dt)
        self.gain = float(gain)
        self.bring = ring_incidence(self.n)
        num, den = prewarped_bandpass_coefficients(
            f0_hz=f0_hz, zeta=zeta, dt=dt, gain=gain
        )
        # Direct-form II transposed per edge: s1, s2 state vectors.
        self._num = num
        self._den = den
        self.reset()

    def reset(self) -> None:
        self._s1 = np.zeros(self.n, dtype=float)
        self._s2 = np.zeros(self.n, dtype=float)

    def step(self, omega: Sequence[float]) -> np.ndarray:
        omega_v = np.asarray(omega, dtype=float)
        if omega_v.shape != (self.n,):
            raise ValueError(f"omega must have shape ({self.n},)")
        if not np.all(np.isfinite(omega_v)):
            raise ValueError("omega must contain only finite values")
        edge_input = self.bring.T @ omega_v
        b0, b1, b2 = self._num
        a1, a2 = self._den[1], self._den[2]
        # Direct-form II transposed update per edge.
        outputs = b0 * edge_input + self._s1
        self._s1 = b1 * edge_input - a1 * outputs + self._s2
        self._s2 = b2 * edge_input - a2 * outputs
        command = -self.bring @ outputs
        return command
