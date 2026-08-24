"""Declared M/D base convention (R478 Phase 0A).

Motivation: ``GENCLS.M`` / ``GENCLS.D`` are base-converted power
parameters in ANDES. The device card carries device-base values
(``S_n,i``, ``H_i``, ``M_i = 2 H_i``, ``D_i``) while the runtime arrays
``GENCLS.M.v`` / ``GENCLS.D.v`` are system-base. Before R478 the V4
reset/step path mixed the two bases: it anchored substep interpolation
on the unconverted device-base ``M0`` and wrote device-base values
straight into the runtime arrays, so a zero first action changed
runtime inertia while the reported action increment stayed zero (and the
post-setup heterogeneous D write silently halved runtime damping).

Convention (frozen):

- controller math (``M0``, ``D0``, action decode, clamps, rewards) stays
  on the DEVICE base (paper Eq.12 semantics);
- every value crossing the ANDES boundary (runtime M/D arrays, telemetry
  readback) is SYSTEM base;
- conversion happens exactly once per boundary crossing:

  ``x_sys = x_dev * S_n / S_b``  and  ``x_dev = x_sys * S_b / S_n``.

Failure modes: a caller that mixes bases silently halves or doubles
runtime inertia or damping. The seven invariant tests in
``tests/test_v4_md_convention_invariants.py`` lock the boundary; any
future edit must keep them green.
"""

from __future__ import annotations

import numpy as np

SYSTEM_BASE_MVA: float = 100.0


def _finite_vector(values, *, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty vector")
    return array


def _check_base(mva: float, *, name: str) -> float:
    if not np.isfinite(mva) or mva <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return float(mva)


def device_to_system(
    values,
    *,
    device_mva: float,
    system_mva: float = SYSTEM_BASE_MVA,
) -> np.ndarray:
    """Convert device-base M/D values to the system base."""
    array = _finite_vector(values, name="values")
    device_mva = _check_base(device_mva, name="device_mva")
    system_mva = _check_base(system_mva, name="system_mva")
    return array * (device_mva / system_mva)


def system_to_device(
    values,
    *,
    device_mva: float,
    system_mva: float = SYSTEM_BASE_MVA,
) -> np.ndarray:
    """Convert system-base M/D readbacks back to the device base."""
    array = _finite_vector(values, name="values")
    device_mva = _check_base(device_mva, name="device_mva")
    system_mva = _check_base(system_mva, name="system_mva")
    return array * (system_mva / device_mva)
