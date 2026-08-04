"""Pure calculations for the R294 full-DAE M/D/P authority map."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def physical_coordinate_matrix() -> np.ndarray:
    """Return common, inter-area, and two within-area orthonormal rows."""

    root_two = np.sqrt(2.0)
    return np.asarray(
        [
            [0.5, 0.5, 0.5, 0.5],
            [0.5, 0.5, -0.5, -0.5],
            [1.0 / root_two, -1.0 / root_two, 0.0, 0.0],
            [0.0, 0.0, 1.0 / root_two, -1.0 / root_two],
        ],
        dtype=float,
    )


def coordinate_trace(frequency_deviation_hz: Sequence[Sequence[float]]) -> np.ndarray:
    """Transform four VSG frequency-deviation traces to physical coordinates."""

    values = np.asarray(frequency_deviation_hz, dtype=float)
    if values.ndim != 2 or values.shape[1] != 4:
        raise ValueError("frequency_deviation_hz must have shape (time, 4)")
    return values @ physical_coordinate_matrix().T


def paired_authority_metrics(
    baseline_frequency_deviation_hz: Sequence[Sequence[float]],
    plus_frequency_deviation_hz: Sequence[Sequence[float]],
    minus_frequency_deviation_hz: Sequence[Sequence[float]],
    *,
    target_coordinate: str,
    dt_seconds: float,
    fast_steps: int,
) -> dict[str, float]:
    """Compute central sensitivity, cross leakage, and nonlinearity metrics."""

    coordinate_index = {"common": 0, "interarea": 1}
    if target_coordinate not in coordinate_index:
        raise ValueError(f"unknown target_coordinate: {target_coordinate}")
    baseline = coordinate_trace(baseline_frequency_deviation_hz)
    plus = coordinate_trace(plus_frequency_deviation_hz)
    minus = coordinate_trace(minus_frequency_deviation_hz)
    if baseline.shape != plus.shape or baseline.shape != minus.shape:
        raise ValueError("paired trajectory shapes differ")
    if not 1 <= fast_steps <= baseline.shape[0]:
        raise ValueError("fast_steps must fit inside the trace")
    if dt_seconds <= 0.0:
        raise ValueError("dt_seconds must be positive")

    sensitivity = 0.5 * (plus - minus)
    midpoint_error = 0.5 * (plus + minus) - baseline
    target = coordinate_index[target_coordinate]
    off_target = [index for index in range(4) if index != target]

    def l2(values: np.ndarray) -> float:
        return float(np.sqrt(np.sum(np.square(values)) * dt_seconds))

    target_l2 = l2(sensitivity[:, target])
    cross_l2 = l2(sensitivity[:, off_target])
    fast_target_l2 = l2(sensitivity[:fast_steps, target])
    fast_cross_l2 = l2(sensitivity[:fast_steps, off_target])
    sensitivity_l2 = l2(sensitivity)
    nonlinearity_l2 = l2(midpoint_error)
    return {
        "target_l2_hz_sqrt_s": target_l2,
        "target_peak_abs_hz": float(np.max(np.abs(sensitivity[:, target]))),
        "cross_l2_hz_sqrt_s": cross_l2,
        "cross_target_l2_ratio": cross_l2 / max(target_l2, 1e-30),
        "fast_target_l2_hz_sqrt_s": fast_target_l2,
        "fast_target_peak_abs_hz": float(
            np.max(np.abs(sensitivity[:fast_steps, target]))
        ),
        "fast_cross_target_l2_ratio": fast_cross_l2
        / max(fast_target_l2, 1e-30),
        "midpoint_nonlinearity_ratio": nonlinearity_l2
        / max(sensitivity_l2, 1e-12),
    }


def aggregate_authority(
    rows: Sequence[Mapping[str, object]],
    *,
    relevance_ratio: float,
    linearity_median_max: float,
    linearity_worst_max: float,
) -> dict[str, object]:
    """Aggregate pointwise metrics and apply the frozen relative screen."""

    if not rows:
        raise ValueError("rows cannot be empty")
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for row in rows:
        key = (str(row["coordinate"]), str(row["actuator"]))
        grouped.setdefault(key, []).append(row)

    summaries: dict[str, dict[str, dict[str, object]]] = {}
    for (coordinate, actuator), items in grouped.items():
        metrics = [item["metrics"] for item in items]
        target = np.asarray(
            [float(metric["target_l2_hz_sqrt_s"]) for metric in metrics]
        )
        cross = np.asarray(
            [float(metric["cross_target_l2_ratio"]) for metric in metrics]
        )
        nonlinearity = np.asarray(
            [float(metric["midpoint_nonlinearity_ratio"]) for metric in metrics]
        )
        summaries.setdefault(coordinate, {})[actuator] = {
            "scenario_count": len(items),
            "target_l2_median": float(np.median(target)),
            "target_l2_min": float(np.min(target)),
            "target_l2_max": float(np.max(target)),
            "cross_target_ratio_median": float(np.median(cross)),
            "cross_target_ratio_max": float(np.max(cross)),
            "nonlinearity_ratio_median": float(np.median(nonlinearity)),
            "nonlinearity_ratio_max": float(np.max(nonlinearity)),
        }

    coordinate_decisions: dict[str, object] = {}
    all_linearity_pass = True
    for coordinate, actuators in summaries.items():
        best = max(float(row["target_l2_median"]) for row in actuators.values())
        dominant = max(
            actuators,
            key=lambda name: float(actuators[name]["target_l2_median"]),
        )
        relevant: list[str] = []
        for actuator, summary in actuators.items():
            ratio = float(summary["target_l2_median"]) / max(best, 1e-30)
            summary["relative_to_best_median_gain"] = ratio
            summary["budget_relevant"] = ratio >= relevance_ratio
            summary["trajectory_linearity_pass"] = bool(
                float(summary["nonlinearity_ratio_median"])
                <= linearity_median_max
                and float(summary["nonlinearity_ratio_max"])
                <= linearity_worst_max
            )
            if summary["budget_relevant"]:
                relevant.append(actuator)
                all_linearity_pass = bool(
                    all_linearity_pass and summary["trajectory_linearity_pass"]
                )
        coordinate_decisions[coordinate] = {
            "dominant_budget_normalized_actuator": dominant,
            "budget_relevant_actuators": sorted(relevant),
            "actuators": actuators,
        }

    return {
        "coordinates": coordinate_decisions,
        "trajectory_model_decision": (
            "TRAJECTORY-LOCAL-LINEARIZATION-ELIGIBLE"
            if all_linearity_pass
            else "TRAJECTORY-LINEARIZATION-NO-GO"
        ),
    }
