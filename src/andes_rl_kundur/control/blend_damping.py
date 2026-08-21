"""Fixed and time-varying A/B blend controllers for the V2 solving gate (R408).

Motivation
----------
The V2 problem set (tmp/yang_md_decoupling_marl/gpt_pro_math_abstraction_v2.md)
recorded two single-family trade-off curves with opposite directions: the
first-order high-pass family (structure A, R406) passes the differential
endpoint but misses probe-cross, and the second-order ring-edge bandpass
(structure B, R407) passes probe-cross but misses differential.  The external
solver candidates B1 (fixed parallel blend) and E1 (time-varying blend) mix
the two frozen structures before the common normalized-action clip and the
feasibility-native energy-port map.

Definitions (frozen for R408)
-----------------------------
- Structure A = HPDampingDistributedController at alpha=0.85, ks=1, kc=1,
  kp=4.0, ki=0.8 (the R406 grid point alpha=0.85, registered endpoints
  r_d=0.9220 / r_cross=1.3136).
- Structure B = RingBandpassDamping at K=2, zeta=0.35, f0=0.4 Hz (the R407
  grid point K=2, registered endpoints r_d=1.0346 / r_cross=0.6778),
  with the R407 adapter clip at +/-0.70.
- B1: q = clip(qA + 0.70 * qB, +/-0.70) at every step.
- E1: q = clip(g(t)*qA + (1-g(t))*qB, +/-0.70) with
  g(t) = 1 for t <= 3.6 s, cosine fade over (3.6, 4.0) s, 0 for t >= 4.0 s;
  both sub-controllers run continuously (no reset at the cross-fade).

Failure modes
-------------
- Non-finite input or wrong shape raises instead of silently steering.
- The sub-controllers own their internal state; a blend controller created
  once per job runs the whole 50-step episode without reset.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np

ACTION_CLIP = 0.70
FADE_START_S = 3.6
FADE_END_S = 4.0
B1_B_WEIGHT = 0.70


class DampingLaw(Protocol):
    """Minimal protocol: one normalized action vector per time step."""

    def act(
        self,
        *,
        frequencies_hz: np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray: ...


class FixedBlendController:
    """B1: fixed parallel A/B blend, mixed before the common clip."""

    architecture = "fixed_blend_b1"

    def __init__(
        self,
        *,
        a_controller: DampingLaw,
        b_controller: DampingLaw,
        b_weight: float = B1_B_WEIGHT,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self._a = a_controller
        self._b = b_controller
        self._weight = float(b_weight)
        self._clip = float(action_clip)
        if not np.isfinite(self._weight) or not 0.0 < self._clip <= 1.0:
            raise ValueError("weight must be finite and clip inside (0, 1]")

    def act(
        self,
        *,
        frequencies_hz: np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        qa = self._a.act(frequencies_hz=frequencies_hz, dt_seconds=dt_seconds)
        qb = self._b.act(frequencies_hz=frequencies_hz, dt_seconds=dt_seconds)
        return np.clip(qa + self._weight * qb, -self._clip, self._clip)


class TimeVaryingBlendController:
    """E1: cosine cross-faded A/B blend; both laws run without reset."""

    architecture = "time_varying_blend_e1"

    def __init__(
        self,
        *,
        a_controller: DampingLaw,
        b_controller: DampingLaw,
        fade_start_s: float = FADE_START_S,
        fade_end_s: float = FADE_END_S,
        action_clip: float = ACTION_CLIP,
    ) -> None:
        self._a = a_controller
        self._b = b_controller
        self._start = float(fade_start_s)
        self._end = float(fade_end_s)
        self._clip = float(action_clip)
        if (
            not 0.0 <= self._start < self._end
            or not 0.0 < self._clip <= 1.0
        ):
            raise ValueError("fade window must satisfy 0 <= start < end")
        self._elapsed = 0.0

    def reset(self) -> None:
        self._elapsed = 0.0

    def _gate(self) -> float:
        if self._elapsed <= self._start:
            return 1.0
        if self._elapsed >= self._end:
            return 0.0
        return 0.5 * (
            1.0
            + np.cos(
                np.pi * (self._elapsed - self._start) / (self._end - self._start)
            )
        )

    def act(
        self,
        *,
        frequencies_hz: np.ndarray,
        dt_seconds: float,
    ) -> np.ndarray:
        dt = float(dt_seconds)
        if not np.isfinite(dt) or dt <= 0.0:
            raise ValueError("dt_seconds must be finite and positive")
        qa = self._a.act(frequencies_hz=frequencies_hz, dt_seconds=dt_seconds)
        qb = self._b.act(frequencies_hz=frequencies_hz, dt_seconds=dt_seconds)
        gate = self._gate()
        action = np.clip(
            gate * qa + (1.0 - gate) * qb,
            -self._clip,
            self._clip,
        )
        self._elapsed += dt
        return action
