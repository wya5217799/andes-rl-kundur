from __future__ import annotations

import math

import numpy as np

from andes_rl_kundur.evaluation.relative_rocof_margin import (
    esd_active_power_input_matrix,
    graph_coordinate_audit,
    ideal_swing_routh_margin,
    sampled_closed_loop_matrix,
    sampled_rocof_transfer,
)


RING = {0: (1, 3), 1: (0, 2), 2: (1, 3), 3: (0, 2)}


def test_ring_common_kernel_and_differential_spectrum() -> None:
    audit = graph_coordinate_audit(RING, device_count=4)
    assert audit["symmetry_max_abs"] == 0.0
    assert audit["common_kernel_max_abs"] == 0.0
    np.testing.assert_allclose(audit["eigenvalues"], [0.0, 1.0, 1.0, 2.0], atol=1e-12)


def test_sampled_filter_is_positive_real_inside_nyquist() -> None:
    values = [
        sampled_rocof_transfer(
            frequency,
            sample_period_s=0.2,
            filter_time_constant_s=0.2,
        )
        for frequency in np.linspace(1e-6, 2.5 - 1e-6, 1000)
    ]
    assert min(value.real for value in values) > 0.0


def test_ideal_swing_margin_increases_with_nonnegative_gain() -> None:
    zero = ideal_swing_routh_margin(
        inertia=2.0,
        damping=0.5,
        synchronizing_stiffness=3.0,
        filter_time_constant_s=0.2,
        graph_eigenvalue=2.0,
        residual_gain=0.0,
    )
    positive = ideal_swing_routh_margin(
        inertia=2.0,
        damping=0.5,
        synchronizing_stiffness=3.0,
        filter_time_constant_s=0.2,
        graph_eigenvalue=2.0,
        residual_gain=0.4,
    )
    assert zero["stable"] is True
    assert positive["stable"] is True
    assert positive["routh_margin"] > zero["routh_margin"]
    assert positive["routh_margin_gain_slope"] > 0.0


def test_esd_input_map_and_sampled_closed_loop_shape() -> None:
    names = ["plant"] + [f"Ipout_y ESD1 device {index}" for index in range(4)]
    b = esd_active_power_input_matrix(
        names,
        device_count=4,
        active_current_lag_seconds=0.02,
        sensed_voltage_pu=1.0,
    )
    np.testing.assert_allclose(b[1:, :], 50.0 * np.eye(4))
    a = -np.eye(5)
    c = np.zeros((4, 5))
    c[:, 0] = 1.0
    laplacian = np.asarray(graph_coordinate_audit(RING, device_count=4)["laplacian"])
    closed = sampled_closed_loop_matrix(
        a,
        b,
        c,
        laplacian,
        sample_period_s=0.2,
        filter_time_constant_s=0.2,
        kp_system_pu_per_hz=2.0,
        ki_system_pu_per_hz_s=0.2,
        sync_gain_system_pu_per_hz=1.0,
        consensus_gain_per_s=1.0,
        relative_rocof_gain_system_pu_s_per_hz=0.4,
    )
    assert closed.shape == (17, 17)
    assert np.all(np.isfinite(closed))


def test_sampled_filter_anchor_matches_implemented_alpha() -> None:
    frequency = 1.1352719219086884
    value = sampled_rocof_transfer(
        frequency,
        sample_period_s=0.2,
        filter_time_constant_s=0.2,
    )
    assert math.isclose(abs(value), 4.076288338306142, rel_tol=1e-12)
    assert value.real > 0.0
