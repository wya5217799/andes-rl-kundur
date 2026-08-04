import numpy as np
import pytest

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.coupling_aware_power import (
    CentralizedCouplingAwarePI,
    DistributedDAPIController,
    row_normalized_laplacian,
)


RING = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}


def test_normalized_ring_laplacian_preserves_common_and_interarea_coordinates():
    laplacian = row_normalized_laplacian(RING, device_count=4)
    np.testing.assert_allclose(laplacian @ np.ones(4), 0.0, atol=1e-12)
    interarea = np.array([1.0, 1.0, -1.0, -1.0])
    np.testing.assert_allclose(laplacian @ interarea, interarea, atol=1e-12)


def test_laplacian_rejects_asymmetric_or_disconnected_graphs():
    with pytest.raises(ValueError, match="undirected"):
        row_normalized_laplacian({0: [1], 1: [2], 2: [1]}, device_count=3)
    with pytest.raises(ValueError, match="connected"):
        row_normalized_laplacian({0: [1], 1: [0], 2: [3], 3: [2]}, device_count=4)


def test_central_controller_reduces_to_equal_common_request_for_uniform_frequency():
    controller = CentralizedCouplingAwarePI(
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=2.0,
        ki_system_pu_per_hz_s_per_device=0.2,
        sync_gain_system_pu_per_hz=1.0,
    )
    request = controller.act(frequencies_hz=[59.9] * 4, dt_seconds=0.2)
    np.testing.assert_allclose(request, np.full(4, 0.204), atol=1e-12)


def test_distributed_output_is_local_and_independent():
    first = DistributedDAPIController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=2.0,
        ki_system_pu_per_hz_s_per_device=0.2,
        sync_gain_system_pu_per_hz=1.0,
        consensus_gain_per_s=1.0,
    )
    second = DistributedDAPIController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=2.0,
        ki_system_pu_per_hz_s_per_device=0.2,
        sync_gain_system_pu_per_hz=1.0,
        consensus_gain_per_s=1.0,
    )
    reference = first.act(frequencies_hz=[59.9, 60.0, 60.2, 60.0], dt_seconds=0.2)
    changed_non_neighbour = second.act(
        frequencies_hz=[59.9, 60.0, 59.5, 60.0],
        dt_seconds=0.2,
    )
    assert reference[0] == pytest.approx(changed_non_neighbour[0])
    assert not np.allclose(reference, np.full(4, reference[0]))


def test_distributed_antiwindup_blocks_outward_local_integral():
    controller = DistributedDAPIController(
        adjacency=RING,
        device_count=4,
        nominal_frequency_hz=60.0,
        kp_system_pu_per_hz_per_device=0.0,
        ki_system_pu_per_hz_s_per_device=1.0,
        sync_gain_system_pu_per_hz=0.0,
        consensus_gain_per_s=0.0,
    )
    projection = PowerProjection(
        requested_power_system_pu=np.ones(4),
        commanded_power_system_pu=np.full(4, 0.5),
        saturation_reasons=(("power",),) * 4,
    )
    request = controller.act(
        frequencies_hz=[59.0] * 4,
        dt_seconds=0.2,
        previous_projection=projection,
    )
    np.testing.assert_allclose(request, 0.0, atol=1e-12)
