from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.active_power import r272_frozen_bess_contract
from andes_rl_kundur.control.feasibility_native_vsg_action import (
    FeasibilityNativeVSGActionMap,
)
from andes_rl_kundur.control.vsg_energy_port import VSGEnergyPortContract


def _mapper() -> FeasibilityNativeVSGActionMap:
    return FeasibilityNativeVSGActionMap(r272_frozen_bess_contract())


def _map(
    actions: list[float] | np.ndarray,
    *,
    previous: list[float] | np.ndarray | None = None,
    soc: list[float] | np.ndarray | None = None,
    voltage: list[float] | np.ndarray | None = None,
):
    return _mapper().map_action(
        normalized_actions=actions,
        previous_power_system_pu=(
            np.zeros(4) if previous is None else np.asarray(previous, dtype=float)
        ),
        soc=np.full(4, 0.5) if soc is None else np.asarray(soc, dtype=float),
        voltage_pu=(
            np.ones(4) if voltage is None else np.asarray(voltage, dtype=float)
        ),
        dt_seconds=0.2,
    )


def test_execution_contract_is_four_vsg_node_agents_without_aggregation() -> None:
    contract = _mapper().execution_contract()

    assert contract == {
        "actor_count": 4,
        "per_actor_action_dimension": 1,
        "executed_node_action_dimension": 4,
        "action_coordinates": "per_vsg_normalized_feasible_power",
        "central_action_aggregation": False,
        "external_projection_role": "identity_guard_only",
        "training_authorized": False,
    }


def test_residual_execution_contract_is_baseline_anchored_and_decentralized() -> None:
    contract = _mapper().residual_execution_contract()

    assert contract == {
        "actor_count": 4,
        "per_actor_action_dimension": 1,
        "executed_node_action_dimension": 4,
        "action_coordinates": "per_vsg_normalized_feasible_power_residual",
        "baseline_anchor": "feasible_deterministic_power",
        "zero_residual_behavior": "exact_deterministic_baseline",
        "central_action_aggregation": False,
        "external_projection_role": "identity_guard_only",
        "training_authorized": False,
    }


def test_zero_action_is_zero_when_zero_power_is_currently_feasible() -> None:
    result = _map([0.0, 0.0, 0.0, 0.0])

    np.testing.assert_allclose(result.feasible_power_system_pu, np.zeros(4))
    assert result.external_projection_identity is True
    assert result.external_projection.saturation_reasons == ((), (), (), ())


def test_zero_residual_returns_the_feasible_deterministic_baseline() -> None:
    mapper = _mapper()
    baseline = np.asarray([0.10, -0.10, 0.04, -0.04])

    result = mapper.map_residual_action(
        normalized_residual_actions=np.zeros(4),
        baseline_power_system_pu=baseline,
        previous_power_system_pu=baseline,
        soc=np.full(4, 0.5),
        voltage_pu=np.ones(4),
        dt_seconds=0.2,
    )

    np.testing.assert_allclose(result.baseline_power_system_pu, baseline)
    np.testing.assert_allclose(result.feasible_power_system_pu, baseline)
    assert result.external_projection_identity is True
    assert result.external_projection.saturation_reasons == ((), (), (), ())


def test_residual_endpoints_span_only_the_baseline_remaining_headroom() -> None:
    mapper = _mapper()
    previous = np.asarray([0.10, -0.10, 0.0, 0.03])
    soc = np.asarray([0.5, 0.5, 0.2, 0.8])
    voltage = np.asarray([1.0, 0.9, 1.0, 1.0])
    lower, upper = mapper.physical_contract.feasible_power_bounds(
        previous_power_system_pu=previous,
        soc=soc,
        voltage_pu=voltage,
        dt_seconds=0.2,
    )
    baseline = lower + 0.25 * (upper - lower)
    common = {
        "baseline_power_system_pu": baseline,
        "previous_power_system_pu": previous,
        "soc": soc,
        "voltage_pu": voltage,
        "dt_seconds": 0.2,
    }

    positive = mapper.map_residual_action(
        normalized_residual_actions=np.ones(4), **common
    )
    negative = mapper.map_residual_action(
        normalized_residual_actions=-np.ones(4), **common
    )

    np.testing.assert_allclose(positive.feasible_power_system_pu, upper, atol=1e-12)
    np.testing.assert_allclose(negative.feasible_power_system_pu, lower, atol=1e-12)


def test_one_residual_changes_only_its_own_vsg_command() -> None:
    mapper = _mapper()
    baseline = np.asarray([0.10, -0.10, 0.04, -0.04])
    common = {
        "baseline_power_system_pu": baseline,
        "previous_power_system_pu": baseline,
        "soc": np.full(4, 0.5),
        "voltage_pu": np.ones(4),
        "dt_seconds": 0.2,
    }

    nominal = mapper.map_residual_action(
        normalized_residual_actions=np.zeros(4), **common
    )
    changed = mapper.map_residual_action(
        normalized_residual_actions=np.asarray([0.0, 0.5, 0.0, 0.0]), **common
    )

    delta = changed.feasible_power_system_pu - nominal.feasible_power_system_pu
    assert delta[1] > 0.0
    np.testing.assert_allclose(delta[[0, 2, 3]], 0.0, atol=1e-12)


def test_four_residuals_span_common_and_three_differential_coordinates() -> None:
    mapper = _mapper()
    directions = np.asarray(
        [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, -1.0, -1.0],
            [1.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, -1.0],
        ]
    )
    common = {
        "baseline_power_system_pu": np.zeros(4),
        "previous_power_system_pu": np.zeros(4),
        "soc": np.full(4, 0.5),
        "voltage_pu": np.ones(4),
        "dt_seconds": 0.2,
    }
    commanded_directions = np.column_stack(
        [
            mapper.map_residual_action(
                normalized_residual_actions=0.25 * direction, **common
            ).feasible_power_system_pu
            for direction in directions
        ]
    )

    assert np.linalg.matrix_rank(commanded_directions, tol=1e-12) == 4
    np.testing.assert_allclose(
        np.sum(commanded_directions[:, 1:], axis=0), 0.0, atol=1e-12
    )


def test_residual_map_fails_closed_on_an_infeasible_deterministic_baseline() -> None:
    mapper = _mapper()
    previous = np.zeros(4)
    soc = np.full(4, 0.5)
    voltage = np.ones(4)
    _lower, upper = mapper.physical_contract.feasible_power_bounds(
        previous_power_system_pu=previous,
        soc=soc,
        voltage_pu=voltage,
        dt_seconds=0.2,
    )
    infeasible_baseline = upper.copy()
    infeasible_baseline[0] += 1.0e-6

    with pytest.raises(ValueError, match="baseline power"):
        mapper.map_residual_action(
            normalized_residual_actions=np.zeros(4),
            baseline_power_system_pu=infeasible_baseline,
            previous_power_system_pu=previous,
            soc=soc,
            voltage_pu=voltage,
            dt_seconds=0.2,
        )


def test_residual_outer_projection_is_identity_under_random_feasible_states() -> None:
    rng = np.random.default_rng(43)
    mapper = _mapper()
    for _ in range(250):
        previous = rng.uniform(-0.30, 0.30, size=4)
        soc = rng.uniform(0.20, 0.80, size=4)
        voltage = rng.uniform(0.70, 1.10, size=4)
        lower, upper = mapper.physical_contract.feasible_power_bounds(
            previous_power_system_pu=previous,
            soc=soc,
            voltage_pu=voltage,
            dt_seconds=0.2,
        )
        baseline = lower + rng.uniform(0.0, 1.0, size=4) * (upper - lower)
        mapped = mapper.map_residual_action(
            normalized_residual_actions=rng.uniform(-1.0, 1.0, size=4),
            baseline_power_system_pu=baseline,
            previous_power_system_pu=previous,
            soc=soc,
            voltage_pu=voltage,
            dt_seconds=0.2,
        )

        assert mapped.external_projection_identity is True
        assert mapped.external_projection.saturation_reasons == ((), (), (), ())
        assert np.all(mapped.feasible_power_system_pu >= lower)
        assert np.all(mapped.feasible_power_system_pu <= upper)


def test_each_actor_spans_its_exact_current_feasible_interval() -> None:
    mapper = _mapper()
    common = {
        "previous_power_system_pu": np.asarray([0.10, -0.10, 0.0, 0.03]),
        "soc": np.asarray([0.5, 0.5, 0.2, 0.8]),
        "voltage_pu": np.asarray([1.0, 0.9, 1.0, 1.0]),
        "dt_seconds": 0.2,
    }
    lower, upper = mapper.physical_contract.feasible_power_bounds(
        previous_power_system_pu=common["previous_power_system_pu"],
        soc=common["soc"],
        voltage_pu=common["voltage_pu"],
        dt_seconds=common["dt_seconds"],
    )

    positive = mapper.map_action(normalized_actions=np.ones(4), **common)
    negative = mapper.map_action(normalized_actions=-np.ones(4), **common)

    np.testing.assert_allclose(positive.feasible_power_system_pu, upper, atol=1e-12)
    np.testing.assert_allclose(negative.feasible_power_system_pu, lower, atol=1e-12)
    assert positive.external_projection.saturation_reasons == ((), (), (), ())
    assert negative.external_projection.saturation_reasons == ((), (), (), ())


def test_one_actor_action_changes_only_its_own_vsg_command() -> None:
    nominal = _map([0.0, 0.0, 0.0, 0.0])
    changed = _map([0.0, 0.5, 0.0, 0.0])

    delta = changed.feasible_power_system_pu - nominal.feasible_power_system_pu
    assert delta[1] > 0.0
    np.testing.assert_allclose(delta[[0, 2, 3]], 0.0, atol=1e-12)


def test_four_node_actions_span_common_and_three_differential_coordinates() -> None:
    directions = np.asarray(
        [
            [1.0, 1.0, 1.0, 1.0],
            [1.0, 1.0, -1.0, -1.0],
            [1.0, -1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, -1.0],
        ],
        dtype=float,
    )
    commanded_directions = np.column_stack(
        [_map(0.25 * direction).feasible_power_system_pu for direction in directions]
    )

    assert np.linalg.matrix_rank(commanded_directions, tol=1e-12) == 4
    np.testing.assert_allclose(
        np.sum(commanded_directions[:, 1:], axis=0),
        0.0,
        atol=1e-12,
    )


def test_outer_vsg_port_projection_is_identity_under_random_feasible_states() -> None:
    rng = np.random.default_rng(42)
    mapper = _mapper()
    port = VSGEnergyPortContract(mapper.physical_contract)
    for _ in range(250):
        previous = rng.uniform(-0.30, 0.30, size=4)
        soc = rng.uniform(0.20, 0.80, size=4)
        voltage = rng.uniform(0.70, 1.10, size=4)
        normalized = rng.uniform(-1.0, 1.0, size=4)
        mapped = mapper.map_action(
            normalized_actions=normalized,
            previous_power_system_pu=previous,
            soc=soc,
            voltage_pu=voltage,
            dt_seconds=0.2,
        )
        dispatch = port.dispatch(
            requested_power_system_pu=mapped.feasible_power_system_pu,
            previous_power_system_pu=previous,
            soc=soc,
            voltage_pu=voltage,
            sampled_omega_pu=np.ones(4),
            baseline_pref_system_pu=np.full(4, 0.5),
            dt_seconds=0.2,
        )

        np.testing.assert_allclose(
            dispatch.commanded_power_system_pu,
            mapped.feasible_power_system_pu,
            rtol=0.0,
            atol=1e-12,
        )
        assert dispatch.saturation_reasons == ((), (), (), ())
        assert mapped.external_projection_identity is True


@pytest.mark.parametrize(
    "actions",
    [
        [1.01, 0.0, 0.0, 0.0],
        [-1.01, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0],
        [0.0, 0.0, float("nan"), 0.0],
    ],
)
def test_action_map_fails_closed_instead_of_silently_clipping_policy_output(
    actions: list[float],
) -> None:
    with pytest.raises(ValueError, match="normalized actions"):
        _map(actions)


@pytest.mark.parametrize(
    ("soc", "voltage", "message"),
    [
        ([-0.01, 0.5, 0.5, 0.5], [1.0] * 4, "soc"),
        ([0.5] * 4, [-0.01, 1.0, 1.0, 1.0], "voltage"),
    ],
)
def test_action_map_fails_closed_on_invalid_physical_state(
    soc: list[float],
    voltage: list[float],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _map([0.0] * 4, soc=soc, voltage=voltage)
