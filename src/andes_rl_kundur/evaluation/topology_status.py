"""Safe ANDES topology-status mutation and EIG validity boundary.

R290 established that direct writes to ``Line.u.v`` can bypass model status
propagation even when PFlow and EIG return true.  Future topology experiments
must enter through this small adapter and must treat initialization, residual,
and spectrum checks as one indivisible guard.
"""

from __future__ import annotations

from typing import Any

import numpy as np

R304_TOPOLOGY_OPENED_LINE = {
    "nominal": "none",
    "line_0_out": "Line_0",
    "line_9_out": "Line_9",
}


def r304_topology_label_matches_opened_line(
    topology: Any,
    opened_line: Any,
) -> bool:
    """Return whether the R304 topology label has its unique line meaning."""
    return (
        isinstance(topology, str)
        and isinstance(opened_line, str)
        and R304_TOPOLOGY_OPENED_LINE.get(topology) == opened_line
    )


def apply_line_outage(
    system: Any,
    line_idx: str,
    *,
    refresh_connectivity: bool = False,
) -> None:
    """Open one line through the ANDES model setter, never by array mutation."""

    system.Line.set("u", line_idx, 0.0, attr="v")
    if refresh_connectivity:
        system.connectivity(info=False)


def _max_abs(values: Any) -> float | None:
    array = np.asarray(values)
    if array.size == 0 or not np.all(np.isfinite(array)):
        return None
    return float(np.max(np.abs(array)))


def eig_validity_guard(
    system: Any,
    *,
    positive_real_tolerance: float = 1e-7,
) -> dict[str, Any]:
    """Combine all R290-required initialization and spectrum validity checks."""

    max_f = _max_abs(system.dae.f)
    max_g = _max_abs(system.dae.g)
    init_tolerance = float(system.TDS.config.tol)
    residual_pass = bool(
        max_f is not None
        and max_g is not None
        and max(max_f, max_g) < init_tolerance
    )
    initialization_pass = bool(
        system.TDS.test_ok is True
        and int(system.exit_code) == 0
        and residual_pass
    )

    eigenvalues = np.asarray(system.EIG.mu)
    spectrum_finite = bool(
        eigenvalues.size
        and np.all(np.isfinite(np.real(eigenvalues)))
        and np.all(np.isfinite(np.imag(eigenvalues)))
    )
    positive_count = (
        int(np.count_nonzero(np.real(eigenvalues) > positive_real_tolerance))
        if spectrum_finite
        else 0
    )
    spectrum_pass = bool(spectrum_finite and positive_count == 0)
    return {
        "passed": bool(initialization_pass and spectrum_pass),
        "initialization_pass": initialization_pass,
        "tds_test_ok": system.TDS.test_ok is True,
        "system_exit_code": int(system.exit_code),
        "initialization_tolerance": init_tolerance,
        "dae_max_abs_f": max_f,
        "dae_max_abs_g": max_g,
        "residual_pass": residual_pass,
        "spectrum_finite": spectrum_finite,
        "positive_real_tolerance": positive_real_tolerance,
        "positive_real_count": positive_count,
        "max_real": (
            float(np.max(np.real(eigenvalues))) if spectrum_finite else None
        ),
        "spectrum_pass": spectrum_pass,
    }
