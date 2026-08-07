"""Pure trace handling for the model-first deterministic physical bridge.

The module converts physical 60-Hz readbacks into the frozen inertia-weighted
coordinates, checks ESD1 limiter telemetry, and computes bounded bridge
endpoints. It reads no repository artifact, runs no simulator, and owns no
scientific classification.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from andes_rl_kundur.env.andes.model_first_contract import (
    weighted_common_differential_transform,
)


@dataclass(frozen=True)
class BridgeTraceSummary:
    """Primary and physical diagnostic endpoints for one finite trace."""

    common_coordinate_iae: float
    differential_coordinate_energy: float
    mean_frequency_iae_hz_seconds: float
    maximum_pairwise_frequency_deviation_hz: float
    controller_engaged: bool
    maximum_requested_node_power_system_pu: float
    maximum_achieved_node_power_system_pu: float
    maximum_achieved_fleet_imbalance_system_pu: float


def _finite_matrix(values: object, *, name: str, columns: int = 4) -> np.ndarray:
    matrix = np.asarray(values, dtype=float)
    if (
        matrix.ndim != 2
        or matrix.shape[0] < 1
        or matrix.shape[1] != columns
        or not np.all(np.isfinite(matrix))
    ):
        raise ValueError(f"{name} must be a non-empty finite matrix with {columns} columns")
    return matrix


def frequency_coordinate_trace(
    frequency_hz: object,
    *,
    reference_frequency_hz: object,
    inertia_system: object,
    physical_nominal_frequency_hz: float = 60.0,
) -> np.ndarray:
    """Return point-referenced inertia-weighted frequency coordinates."""

    frequency = _finite_matrix(frequency_hz, name="frequency_hz")
    reference = np.asarray(reference_frequency_hz, dtype=float)
    nominal = float(physical_nominal_frequency_hz)
    if reference.shape != (4,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_frequency_hz must contain four finite values")
    if not np.isfinite(nominal) or nominal <= 0.0:
        raise ValueError("physical_nominal_frequency_hz must be positive and finite")
    transform = weighted_common_differential_transform(inertia_system)
    if transform.forward.shape != (4, 4):
        raise ValueError("inertia_system must define exactly four coordinates")
    per_unit_deviation = (frequency - reference.reshape(1, 4)) / nominal
    return (transform.forward @ per_unit_deviation.T).T


def bridge_internal_limiter_active(internal: Mapping[str, object]) -> bool:
    """Return whether current or recovery telemetry shows an active limiter."""

    required = ("Ipul", "Ipcmd_y", "Ipmin", "Ipmax", "Fvl", "Fvh", "Ffl", "Ffh")
    missing = [name for name in required if name not in internal]
    if missing:
        raise ValueError(f"missing ESD1 limiter telemetry: {', '.join(missing)}")
    values = {name: np.asarray(internal[name], dtype=float) for name in required}
    if any(value.shape != (4,) or not np.all(np.isfinite(value)) for value in values.values()):
        raise ValueError("ESD1 limiter telemetry must contain finite four-vectors")
    if not np.allclose(values["Ipul"], values["Ipcmd_y"], rtol=0.0, atol=1.0e-8):
        return True
    if np.any(values["Ipcmd_y"] < values["Ipmin"] - 1.0e-8) or np.any(
        values["Ipcmd_y"] > values["Ipmax"] + 1.0e-8
    ):
        return True
    return any(
        not np.allclose(values[name], np.ones(4), rtol=0.0, atol=1.0e-12)
        for name in ("Fvl", "Fvh", "Ffl", "Ffh")
    )


def summarize_bridge_trace(
    *,
    coordinate_outputs: object,
    frequency_hz: object,
    reference_frequency_hz: object,
    requested_node_power: object,
    achieved_node_power: object,
    sample_period_seconds: float,
) -> BridgeTraceSummary:
    """Compute the frozen common, differential, and physical trace endpoints."""

    coordinates = _finite_matrix(coordinate_outputs, name="coordinate_outputs")
    frequency = _finite_matrix(frequency_hz, name="frequency_hz")
    requested = _finite_matrix(requested_node_power, name="requested_node_power")
    achieved = _finite_matrix(achieved_node_power, name="achieved_node_power")
    if not (coordinates.shape == frequency.shape == requested.shape == achieved.shape):
        raise ValueError("bridge trace arrays must have the same shape")
    reference = np.asarray(reference_frequency_hz, dtype=float)
    if reference.shape != (4,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_frequency_hz must contain four finite values")
    sample_period = float(sample_period_seconds)
    if not np.isfinite(sample_period) or sample_period <= 0.0:
        raise ValueError("sample_period_seconds must be positive and finite")

    mean_frequency_deviation = np.mean(frequency - reference.reshape(1, 4), axis=1)
    pairwise_deviation = np.ptp(frequency, axis=1)
    return BridgeTraceSummary(
        common_coordinate_iae=float(sample_period * np.sum(np.abs(coordinates[:, 0]))),
        differential_coordinate_energy=float(
            sample_period * np.sum(np.square(coordinates[:, 1:]))
        ),
        mean_frequency_iae_hz_seconds=float(
            sample_period * np.sum(np.abs(mean_frequency_deviation))
        ),
        maximum_pairwise_frequency_deviation_hz=float(np.max(pairwise_deviation)),
        controller_engaged=bool(np.any(np.abs(requested) > 1.0e-12)),
        maximum_requested_node_power_system_pu=float(np.max(np.abs(requested))),
        maximum_achieved_node_power_system_pu=float(np.max(np.abs(achieved))),
        maximum_achieved_fleet_imbalance_system_pu=float(
            np.max(np.abs(np.sum(achieved, axis=1)))
        ),
    )
