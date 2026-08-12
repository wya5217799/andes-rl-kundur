from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.cross_coordinate_decoupler import (
    DistributedCrossCoordinateController,
    LocalDiagonalPIController,
)

RING = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [0, 2]}


def test_distributed_controller_preserves_common_mean_and_zero_sum_differential() -> None:
    controller = DistributedCrossCoordinateController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=2.0,
        ki_system_pu_per_hz_s=0.2,
        sync_gain_system_pu_per_hz=1.0,
        consensus_gain_per_s=1.0,
    )

    action = controller.act(
        frequencies_hz=[59.9, 60.0, 60.2, 59.8],
        dt_seconds=0.2,
    )

    expected_mean_error = np.mean([0.1, 0.0, -0.2, 0.2])
    assert np.mean(action.common_estimate_hz) == pytest.approx(
        expected_mean_error,
        abs=1.0e-12,
    )
    np.testing.assert_allclose(
        np.sum(action.differential_request_system_pu),
        0.0,
        atol=1.0e-12,
    )


def test_local_diagonal_controller_has_independent_per_device_actions() -> None:
    first = LocalDiagonalPIController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=2.0,
        ki_system_pu_per_hz_s=0.2,
    )
    second = LocalDiagonalPIController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=2.0,
        ki_system_pu_per_hz_s=0.2,
    )

    reference = first.act(
        frequencies_hz=[59.9, 60.0, 60.2, 60.0],
        dt_seconds=0.2,
    )
    changed_other_devices = second.act(
        frequencies_hz=[59.9, 59.0, 61.0, 60.5],
        dt_seconds=0.2,
    )

    assert reference.requested_power_system_pu[0] == pytest.approx(
        changed_other_devices.requested_power_system_pu[0]
    )
    np.testing.assert_allclose(reference.differential_request_system_pu, 0.0)


def test_dynamic_average_estimate_tracks_fleet_error_mean_over_time() -> None:
    controller = DistributedCrossCoordinateController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=2.0,
        ki_system_pu_per_hz_s=0.2,
        sync_gain_system_pu_per_hz=0.5,
        consensus_gain_per_s=1.0,
    )

    for frequency in (
        [59.9, 60.1, 60.0, 59.8],
        [59.8, 60.0, 60.3, 59.9],
        [60.1, 60.2, 59.7, 59.8],
    ):
        action = controller.act(frequencies_hz=frequency, dt_seconds=0.2)
        assert np.mean(action.common_estimate_hz) == pytest.approx(
            np.mean(60.0 - np.asarray(frequency)),
            abs=1.0e-12,
        )
        assert np.sum(action.differential_request_system_pu) == pytest.approx(
            0.0,
            abs=1.0e-12,
        )


def test_saturation_blocks_outward_integral_in_both_controllers() -> None:
    projection = PowerProjection(
        requested_power_system_pu=np.ones(4),
        commanded_power_system_pu=np.full(4, 0.5),
        saturation_reasons=(("power",),) * 4,
    )
    local = LocalDiagonalPIController(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=0.0,
        ki_system_pu_per_hz_s=1.0,
    )
    distributed = DistributedCrossCoordinateController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz=0.0,
        ki_system_pu_per_hz_s=1.0,
        sync_gain_system_pu_per_hz=0.0,
        consensus_gain_per_s=1.0,
    )

    for controller in (local, distributed):
        action = controller.act(
            frequencies_hz=[59.0] * 4,
            dt_seconds=0.2,
            previous_projection=projection,
        )
        np.testing.assert_allclose(action.requested_power_system_pu, 0.0)
