"""Independent physical and control endpoints for evaluation traces.

The project's frozen ``paper_grade_axes`` score remains useful as a historical
paper-alignment diagnostic. This module does not change or aggregate that
score. It reports transparent physical quantities directly from the
60-Hz-calibrated trace fields added in R261, plus normalized action effort when
the producing evaluator records ``action_norm``.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _finite_matrix(
    traces: list[dict[str, Any]],
    key: str,
) -> np.ndarray:
    try:
        value = np.asarray([step[key] for step in traces], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"trace steps require a rectangular numeric '{key}'") from exc
    if value.ndim != 2 or value.shape[1] == 0:
        raise ValueError(f"trace field '{key}' must have shape [time, agent]")
    if not np.all(np.isfinite(value)):
        raise ValueError(f"trace field '{key}' contains non-finite values")
    return value


def _sample_interval(time: np.ndarray) -> float:
    if time.size < 2:
        raise ValueError("physical endpoints require at least two trace steps")
    intervals = np.diff(time)
    if np.any(~np.isfinite(intervals)) or np.any(intervals <= 0):
        raise ValueError("trace time must be finite and strictly increasing")
    return float(np.median(intervals))


def _settling_time(
    time: np.ndarray,
    delta_f: np.ndarray,
    *,
    band_hz: float,
) -> float | None:
    inside = np.all(np.abs(delta_f) <= band_hz, axis=1)
    suffix_inside = np.logical_and.accumulate(inside[::-1])[::-1]
    indices = np.flatnonzero(suffix_inside)
    return float(time[indices[0]]) if indices.size else None


def summarise_physical_trace(
    record: dict[str, Any],
    *,
    settling_band_hz: float = 0.05,
) -> dict[str, float | int | bool | None]:
    """Return auditable physical endpoints for one completed trace.

    Frequency fields use ``delta_f_physical_hz`` and therefore the nominal
    frequency encoded by the ANDES case. Integrals use the median sampled
    interval. ``vsg_mean`` is intentionally not called COI because the trace
    does not contain inertia weights.
    """
    if record.get("tds_failed") is True or record.get("completed") is False:
        raise ValueError("refusing physical endpoints for a failed/incomplete trace")
    if record.get("frequency_reporting_basis") != "legacy_control_hz":
        raise ValueError("trace must declare its legacy frequency reporting basis")
    physical_nominal = record.get("andes_nominal_frequency_hz")
    if not isinstance(physical_nominal, (int, float)) or not np.isfinite(physical_nominal):
        raise ValueError("trace must declare a finite ANDES nominal frequency")
    if not np.isfinite(settling_band_hz) or settling_band_hz <= 0:
        raise ValueError("settling_band_hz must be finite and positive")

    traces = record.get("traces")
    if not isinstance(traces, list) or not traces:
        raise ValueError("trace record has no steps")
    if int(record.get("n_steps", len(traces))) != len(traces):
        raise ValueError("n_steps does not match trace payload")

    try:
        time = np.asarray([step["t"] for step in traces], dtype=float)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("trace steps require numeric time") from exc
    dt = _sample_interval(time)
    delta_f = _finite_matrix(traces, "delta_f_physical_hz")

    vsg_mean = np.mean(delta_f, axis=1)
    dispersion = np.std(delta_f, axis=1)
    rocof = np.diff(delta_f, axis=0) / np.diff(time)[:, None]
    normalized_sync_loss = np.mean(np.square(delta_f - vsg_mean[:, None]))

    result: dict[str, float | int | bool | None] = {
        "andes_nominal_frequency_hz": float(physical_nominal),
        "sample_interval_s": dt,
        "n_steps": int(len(traces)),
        "completed": True,
        "worst_bus_peak_abs_hz": float(np.max(np.abs(delta_f))),
        "vsg_mean_peak_abs_hz": float(np.max(np.abs(vsg_mean))),
        "vsg_mean_iae_hz_s": float(np.sum(np.abs(vsg_mean)) * dt),
        "dispersion_rms_hz": float(np.sqrt(np.mean(np.square(dispersion)))),
        "dispersion_ise_hz2_s": float(np.sum(np.square(dispersion)) * dt),
        "normalized_sync_loss_hz2": float(normalized_sync_loss),
        "max_abs_rocof_hz_s": float(np.max(np.abs(rocof))),
        "terminal_worst_bus_abs_hz": float(np.max(np.abs(delta_f[-1]))),
        "settling_band_hz": float(settling_band_hz),
        "settling_time_s": _settling_time(
            time,
            delta_f,
            band_hz=settling_band_hz,
        ),
    }

    if all("action_norm" in step for step in traces):
        actions = np.asarray([step["action_norm"] for step in traces], dtype=float)
        if actions.ndim != 3 or actions.shape[1:] != (delta_f.shape[1], 2):
            raise ValueError("action_norm must have shape [time, agent, 2]")
        if not np.all(np.isfinite(actions)):
            raise ValueError("action_norm contains non-finite values")
        result.update(
            {
                "action_l1_agent_s": float(
                    np.sum(np.mean(np.sum(np.abs(actions), axis=2), axis=1)) * dt
                ),
                "action_total_variation": float(
                    np.sum(
                        np.mean(
                            np.sum(np.abs(np.diff(actions, axis=0)), axis=2),
                            axis=1,
                        )
                    )
                ),
                "action_saturation_fraction": float(
                    np.mean(np.isclose(np.abs(actions), 1.0, rtol=0.0, atol=1e-6))
                ),
            }
        )
    else:
        result.update(
            {
                "action_l1_agent_s": None,
                "action_total_variation": None,
                "action_saturation_fraction": None,
            }
        )
    return result
