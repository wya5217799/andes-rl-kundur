from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.decentralized_dapi import DecentralizedDAPIExecution
from andes_rl_kundur.control.relative_rocof_residual import (
    DecentralizedRelativeRoCoFResidualExecution,
)


ADJACENCY = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}
COMMON = {
    "adjacency": ADJACENCY,
    "device_count": 4,
    "nominal_frequency_hz": 60.0,
    "kp_system_pu_per_hz_per_device": 2.0,
    "ki_system_pu_per_hz_s_per_device": 0.2,
    "sync_gain_system_pu_per_hz": 1.0,
    "consensus_gain_per_s": 1.0,
}


def _controller(gain: float):
    return DecentralizedRelativeRoCoFResidualExecution(
        **COMMON,
        rocof_filter_time_constant_s=0.2,
        relative_rocof_gain_system_pu_s_per_hz=gain,
    )


def test_zero_gain_is_exact_dapi_execution() -> None:
    reference = DecentralizedDAPIExecution(**COMMON)
    candidate = _controller(0.0)
    for frequency in (
        [60.0, 60.0, 60.0, 60.0],
        [60.1, 59.9, 60.05, 59.95],
        [60.04, 59.96, 60.02, 59.98],
    ):
        expected = reference.act(frequencies_hz=frequency, dt_seconds=0.2)
        observed = candidate.act(frequencies_hz=frequency, dt_seconds=0.2)
        assert np.array_equal(observed, expected)


def test_relative_rocof_residual_is_strictly_zero_sum() -> None:
    controller = _controller(0.12212035624810003)
    controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    request = controller.act(
        frequencies_hz=[60.1, 59.9, 60.05, 59.95],
        dt_seconds=0.2,
    )
    residual = controller.last_residual_requests_system_pu
    assert np.max(np.abs(residual)) > 0.0
    assert float(np.sum(residual)) == pytest.approx(0.0, abs=1e-15)
    assert np.array_equal(
        request,
        controller.last_base_requests_system_pu + residual,
    )


def test_each_agent_owns_independent_filter_state() -> None:
    controller = _controller(0.06106017812405001)
    controller.act(frequencies_hz=[60.0] * 4, dt_seconds=0.2)
    controller.act(frequencies_hz=[60.1, 60.0, 60.0, 60.0], dt_seconds=0.2)
    assert controller.agents[0].filtered_rocof_hz_s != 0.0
    assert all(
        controller.agents[index].filtered_rocof_hz_s == 0.0
        for index in (1, 2, 3)
    )


def test_zero_sum_contract_rejects_irregular_or_directed_graph() -> None:
    irregular = {0: [1], 1: [0, 2], 2: [1, 3], 3: [2]}
    directed = {0: [1], 1: [2], 2: [3], 3: [0]}
    for adjacency in (irregular, directed):
        with pytest.raises(ValueError):
            DecentralizedRelativeRoCoFResidualExecution(
                **{**COMMON, "adjacency": adjacency},
                rocof_filter_time_constant_s=0.2,
                relative_rocof_gain_system_pu_s_per_hz=0.1,
            )
