"""Public-seam tests for deterministic physical-bridge trace handling."""

from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.model_first_physical_bridge import (
    bridge_internal_limiter_active,
    frequency_coordinate_trace,
    summarize_bridge_trace,
)


def test_frequency_coordinates_are_zero_referenced_and_inertia_weighted() -> None:
    frequency_hz = np.array(
        [
            [60.0, 60.0, 60.0, 60.0],
            [60.06, 60.06, 60.06, 60.06],
        ]
    )

    coordinates = frequency_coordinate_trace(
        frequency_hz,
        reference_frequency_hz=frequency_hz[0],
        inertia_system=np.ones(4),
    )

    np.testing.assert_allclose(coordinates[0], np.zeros(4), atol=1.0e-15)
    np.testing.assert_allclose(
        coordinates[1],
        np.array([0.002, 0.0, 0.0, 0.0]),
        atol=1.0e-15,
    )


def test_bridge_summary_keeps_common_and_differential_endpoints_separate() -> None:
    frequency_hz = np.array(
        [
            [60.0, 60.0, 60.0, 60.0],
            [60.06, 60.06, 60.06, 60.06],
        ]
    )
    coordinates = np.array(
        [
            [0.0, 0.0, 0.0, 0.0],
            [0.002, 0.001, 0.0, 0.0],
        ]
    )

    summary = summarize_bridge_trace(
        coordinate_outputs=coordinates,
        frequency_hz=frequency_hz,
        reference_frequency_hz=frequency_hz[0],
        requested_node_power=np.array([[0.0] * 4, [0.01, -0.01, 0.0, 0.0]]),
        achieved_node_power=np.array([[0.0] * 4, [0.009, -0.009, 0.0, 0.0]]),
        sample_period_seconds=0.2,
    )

    assert summary.common_coordinate_iae == 0.0004
    assert summary.differential_coordinate_energy == 0.0000002
    assert np.isclose(summary.mean_frequency_iae_hz_seconds, 0.012)
    assert summary.maximum_pairwise_frequency_deviation_hz == 0.0
    assert summary.controller_engaged
    assert summary.maximum_achieved_fleet_imbalance_system_pu == 0.0


def test_internal_limiter_guard_reads_current_and_recovery_layers() -> None:
    inactive = {
        "Ipul": [0.1, -0.1, 0.0, 0.0],
        "Ipcmd_y": [0.1, -0.1, 0.0, 0.0],
        "Ipmin": [-1.0] * 4,
        "Ipmax": [1.0] * 4,
        "Fvl": [1.0] * 4,
        "Fvh": [1.0] * 4,
        "Ffl": [1.0] * 4,
        "Ffh": [1.0] * 4,
    }

    assert not bridge_internal_limiter_active(inactive)
    active = dict(inactive)
    active["Ffl"] = [1.0, 0.5, 1.0, 1.0]
    assert bridge_internal_limiter_active(active)
