from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.headroom_aware_edge_allocation import (
    allocate_edge_flows_with_headroom,
    project_residual_to_zero_sum_box,
)

RING_PHASES = (
    ((0, 1), (2, 3)),
    ((1, 2), (0, 3)),
)


def test_bess_contract_reports_soc_and_ramp_feasible_power_bounds() -> None:
    contract = r272_frozen_bess_contract()

    lower, upper = contract.feasible_power_bounds(
        previous_power_system_pu=[0.0] * 4,
        soc=[0.2, 0.8, 0.5, 0.5],
        voltage_pu=[1.0] * 4,
        dt_seconds=0.2,
    )

    np.testing.assert_allclose(lower, [-0.072, 0.0, -0.072, -0.072], atol=1e-12)
    np.testing.assert_allclose(upper, [0.0, 0.072, 0.072, 0.072], atol=1e-12)


def test_local_edge_allocator_clips_one_flow_using_only_endpoint_headroom() -> None:
    result = allocate_edge_flows_with_headroom(
        base_power_system_pu=[0.0, 0.0],
        requested_edge_flows_system_pu={(0, 1): 0.05},
        edge_phases=(((0, 1),),),
        lower_power_system_pu=[-0.04, -0.04],
        upper_power_system_pu=[0.02, 0.04],
    )

    assert result.allocated_edge_flows_system_pu == {(0, 1): pytest.approx(0.02)}
    np.testing.assert_allclose(result.commanded_power_system_pu, [0.02, -0.02])
    np.testing.assert_allclose(result.residual_power_system_pu, [0.02, -0.02])
    assert float(np.sum(result.residual_power_system_pu)) == pytest.approx(0.0)


def test_local_ring_allocator_is_identity_when_no_edge_needs_curtailment() -> None:
    requested = {(0, 1): 0.03, (1, 2): -0.01, (2, 3): 0.02, (0, 3): -0.04}
    result = allocate_edge_flows_with_headroom(
        base_power_system_pu=[0.01] * 4,
        requested_edge_flows_system_pu=requested,
        edge_phases=RING_PHASES,
        lower_power_system_pu=[-0.2] * 4,
        upper_power_system_pu=[0.2] * 4,
    )

    assert result.allocated_edge_flows_system_pu == pytest.approx(requested)
    np.testing.assert_allclose(
        result.residual_power_system_pu,
        [-0.01, -0.04, 0.03, 0.02],
        atol=1e-12,
    )
    assert float(np.sum(result.residual_power_system_pu)) == pytest.approx(0.0)


def test_zero_sum_box_projection_matches_worked_asymmetric_example() -> None:
    projected = project_residual_to_zero_sum_box(
        target_residual_system_pu=[0.3, -0.1, -0.1, -0.1],
        lower_residual_system_pu=[-0.05, -0.2, -0.2, -0.2],
        upper_residual_system_pu=[0.05, 0.2, 0.2, 0.2],
    )

    np.testing.assert_allclose(
        projected,
        [0.05, -1.0 / 60.0, -1.0 / 60.0, -1.0 / 60.0],
        atol=1e-12,
    )
    assert float(np.sum(projected)) == pytest.approx(0.0, abs=1e-12)


def test_zero_sum_box_projection_rejects_infeasible_box() -> None:
    with pytest.raises(ValueError, match="zero-sum point"):
        project_residual_to_zero_sum_box(
            target_residual_system_pu=[0.0, 0.0],
            lower_residual_system_pu=[0.1, 0.1],
            upper_residual_system_pu=[0.2, 0.2],
        )


def test_local_allocator_rejects_base_outside_feasible_power_box() -> None:
    with pytest.raises(ValueError, match="base power"):
        allocate_edge_flows_with_headroom(
            base_power_system_pu=[0.2, 0.0],
            requested_edge_flows_system_pu={(0, 1): 0.0},
            edge_phases=(((0, 1),),),
            lower_power_system_pu=[-0.1, -0.1],
            upper_power_system_pu=[0.1, 0.1],
        )
