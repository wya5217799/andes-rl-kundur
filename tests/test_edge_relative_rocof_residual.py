from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.edge_relative_rocof_residual import (
    DecentralizedEdgeSelectiveRelativeRoCoFExecution,
)
from andes_rl_kundur.control.relative_rocof_residual import (
    DecentralizedRelativeRoCoFResidualExecution,
)


ADJACENCY = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}
GAIN = 0.24424071249620006
COMMON = {
    "adjacency": ADJACENCY,
    "device_count": 4,
    "nominal_frequency_hz": 60.0,
    "kp_system_pu_per_hz_per_device": 2.0,
    "ki_system_pu_per_hz_s_per_device": 0.2,
    "sync_gain_system_pu_per_hz": 1.0,
    "consensus_gain_per_s": 1.0,
    "rocof_filter_time_constant_s": 0.2,
}


def _edge_controller(extra):
    return DecentralizedEdgeSelectiveRelativeRoCoFExecution(
        **COMMON,
        relative_rocof_gain_system_pu_s_per_hz=GAIN,
        extra_edge_gains_system_pu_s_per_hz=extra,
    )


def _step_pair(controller):
    controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    return controller.act(
        frequencies_hz=[60.1, 59.9, 60.05, 59.95],
        dt_seconds=0.2,
    )


def test_zero_extra_is_exact_base_controller() -> None:
    reference = DecentralizedRelativeRoCoFResidualExecution(
        **COMMON,
        relative_rocof_gain_system_pu_s_per_hz=GAIN,
    )
    candidate = _edge_controller({})
    for frequency in (
        [60.0] * 4,
        [60.1, 59.9, 60.05, 59.95],
        [60.04, 59.96, 60.02, 59.98],
    ):
        expected = reference.act(frequencies_hz=frequency, dt_seconds=0.2)
        observed = candidate.act(frequencies_hz=frequency, dt_seconds=0.2)
        assert np.array_equal(observed, expected)


def test_one_edge_increment_is_local_and_zero_sum() -> None:
    controller = _edge_controller({(0, 1): GAIN})
    request = _step_pair(controller)
    extra = controller.last_extra_requests_system_pu
    assert extra[0] == pytest.approx(-extra[1], abs=1e-15)
    assert np.array_equal(extra[2:], np.zeros(2))
    assert float(np.sum(extra)) == pytest.approx(0.0, abs=1e-15)
    assert np.array_equal(
        request,
        controller.last_base_requests_system_pu
        + controller.last_residual_requests_system_pu
        + extra,
    )


def test_equal_increment_on_every_edge_matches_double_base_gain() -> None:
    edges = {(0, 1): GAIN, (1, 2): GAIN, (2, 3): GAIN, (0, 3): GAIN}
    candidate = _edge_controller(edges)
    reference = DecentralizedRelativeRoCoFResidualExecution(
        **COMMON,
        relative_rocof_gain_system_pu_s_per_hz=2.0 * GAIN,
    )
    for frequency in ([60.0] * 4, [60.1, 59.9, 60.05, 59.95]):
        observed = candidate.act(frequencies_hz=frequency, dt_seconds=0.2)
        expected = reference.act(frequencies_hz=frequency, dt_seconds=0.2)
        assert np.allclose(observed, expected, rtol=0.0, atol=1e-16)


def test_invalid_edge_gain_is_rejected() -> None:
    for extra in ({(0, 2): GAIN}, {(0, 1): -GAIN}, {(1, 0): GAIN, (0, 1): GAIN}):
        with pytest.raises(ValueError):
            _edge_controller(extra)
