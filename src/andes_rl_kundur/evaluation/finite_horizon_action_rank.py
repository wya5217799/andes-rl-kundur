"""Finite-horizon physical action-rank diagnostics from paired trajectories.

The public seam accepts positive/negative action probes, normalizes each pair
by its physical amplitude, projects outputs into registered coordinates, and
returns scale-aware singular-value summaries.  It deliberately evaluates
actuator authority only; it does not score a controller or authorize learning.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np


def _rank_profile(
    matrix: np.ndarray,
    *,
    relative_thresholds: Sequence[float],
) -> dict[str, object]:
    singular_values = np.linalg.svd(matrix, compute_uv=False)
    leading = float(singular_values[0]) if singular_values.size else 0.0
    ratios = (
        singular_values / leading if leading > 0.0 else np.zeros_like(singular_values)
    )
    squared_sum = float(np.sum(np.square(singular_values)))
    stable_rank = squared_sum / (leading * leading) if leading > 0.0 else 0.0
    participation_rank = (
        float(np.sum(singular_values) ** 2) / squared_sum
        if squared_sum > 0.0
        else 0.0
    )
    return {
        "matrix_shape": [int(value) for value in matrix.shape],
        "singular_values": singular_values.tolist(),
        "relative_singular_values": ratios.tolist(),
        "numerical_rank": int(np.linalg.matrix_rank(matrix)),
        "stable_rank": stable_rank,
        "participation_rank": participation_rank,
        "relative_effective_rank": {
            format(float(threshold), "g"): int(np.sum(ratios >= threshold))
            for threshold in sorted(relative_thresholds)
        },
    }


def finite_horizon_action_rank(
    plus_traces: object,
    minus_traces: object,
    *,
    amplitudes: object,
    output_transform: object,
    relative_thresholds: Sequence[float] = (0.1, 0.05, 0.01),
) -> dict[str, object]:
    """Return all/common/differential rank profiles for paired action probes.

    ``plus_traces`` and ``minus_traces`` have shape
    ``(action, time, physical_output)``.  ``output_transform`` maps physical
    outputs to coordinates; its first row is the registered common coordinate
    and all remaining rows are treated as differential outputs.
    """

    plus = np.asarray(plus_traces, dtype=float)
    minus = np.asarray(minus_traces, dtype=float)
    if plus.ndim != 3 or plus.shape != minus.shape:
        raise ValueError("paired traces must share shape (action, time, output)")
    if plus.shape[0] < 1 or plus.shape[1] < 1 or plus.shape[2] < 2:
        raise ValueError("paired traces need actions, samples, and at least two outputs")
    if not np.all(np.isfinite(plus)) or not np.all(np.isfinite(minus)):
        raise ValueError("paired traces must be finite")

    scale = np.asarray(amplitudes, dtype=float)
    if scale.shape != (plus.shape[0],) or not np.all(np.isfinite(scale)) or np.any(
        scale <= 0.0
    ):
        raise ValueError("amplitudes must be finite and positive per action")

    transform = np.asarray(output_transform, dtype=float)
    if (
        transform.ndim != 2
        or transform.shape[1] != plus.shape[2]
        or transform.shape[0] < 2
        or not np.all(np.isfinite(transform))
    ):
        raise ValueError("output_transform must map outputs to common/differential rows")

    thresholds = tuple(float(value) for value in relative_thresholds)
    if not thresholds or any(
        not np.isfinite(value) or value <= 0.0 or value > 1.0
        for value in thresholds
    ):
        raise ValueError("relative_thresholds must lie in (0, 1]")

    sensitivity = 0.5 * (plus - minus) / scale[:, None, None]
    coordinates = sensitivity @ transform.T
    action_count, sample_count, coordinate_count = coordinates.shape
    all_outputs = coordinates.transpose(1, 2, 0).reshape(
        sample_count * coordinate_count, action_count
    )
    common_output = coordinates[:, :, 0].T
    differential_outputs = coordinates[:, :, 1:].transpose(1, 2, 0).reshape(
        sample_count * (coordinate_count - 1), action_count
    )

    return {
        "action_count": int(action_count),
        "sample_count": int(sample_count),
        "physical_output_count": int(plus.shape[2]),
        "coordinate_count": int(coordinate_count),
        "amplitudes": scale.tolist(),
        "all_outputs": _rank_profile(
            all_outputs, relative_thresholds=thresholds
        ),
        "common_output": _rank_profile(
            common_output, relative_thresholds=thresholds
        ),
        "differential_outputs": _rank_profile(
            differential_outputs, relative_thresholds=thresholds
        ),
    }
