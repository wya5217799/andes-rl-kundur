from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.per_vsg_md import (
    LocalNeighbourMDContract,
    LocalNeighbourMDExecution,
    PerVSGMDActionProjector,
    adapt_v4_observations_to_physical,
    local_neighbour_md_candidates,
)


def test_adapter_converts_every_frequency_slot_from_50_to_60_hz() -> None:
    observations = {
        actor: np.asarray(
            [10.0 + actor, 1.0, -2.0, 3.0, -4.0, 5.0, -6.0],
            dtype=np.float32,
        )
        for actor in range(4)
    }

    adapted = adapt_v4_observations_to_physical(observations)

    for actor in range(4):
        assert adapted[actor][0] == observations[actor][0]
        np.testing.assert_allclose(
            adapted[actor][1:],
            np.asarray([1.2, -2.4, 3.6, -4.8, 6.0, -7.2]),
            rtol=0.0,
            atol=1e-6,
        )
        assert adapted[actor] is not observations[actor]


def test_adapter_rejects_nonphysical_or_malformed_inputs() -> None:
    valid = {actor: np.zeros(7, dtype=np.float32) for actor in range(4)}

    with pytest.raises(ValueError, match="physical nominal frequency must be 60"):
        adapt_v4_observations_to_physical(
            valid,
            physical_nominal_frequency_hz=50.0,
        )
    with pytest.raises(ValueError, match="control nominal frequency"):
        adapt_v4_observations_to_physical(
            valid,
            control_nominal_frequency_hz=0.0,
        )
    with pytest.raises(ValueError, match="control nominal frequency must be 50"):
        adapt_v4_observations_to_physical(
            valid,
            control_nominal_frequency_hz=55.0,
        )
    malformed = {actor: row.copy() for actor, row in valid.items()}
    malformed[2][4] = np.nan
    with pytest.raises(ValueError, match="finite"):
        adapt_v4_observations_to_physical(malformed)


def test_deterministic_family_freezes_nine_unique_permission_matched_candidates() -> None:
    candidates = local_neighbour_md_candidates()

    assert len(candidates) == 9
    assert len({candidate.name for candidate in candidates}) == 9
    assert {candidate.inertia_gain for candidate in candidates} == {0.5, 1.0, 2.0}
    assert {candidate.damping_gain for candidate in candidates} == {0.5, 1.0, 2.0}
    assert {candidate.action_slew_limit for candidate in candidates} == {0.25}
    assert {candidate.action_coordinates for candidate in candidates} == {
        ("normalized_delta_M", "normalized_delta_D")
    }


def test_execution_returns_independent_local_md_actions_without_global_pooling() -> None:
    controller = LocalNeighbourMDExecution(
        LocalNeighbourMDContract(inertia_gain=2.0, damping_gain=2.0)
    )
    zero = {actor: np.zeros(7, dtype=np.float32) for actor in range(4)}

    np.testing.assert_array_equal(controller.act(zero), np.zeros((4, 2)))

    local_event = {actor: row.copy() for actor, row in zero.items()}
    local_event[0][1] = 0.4
    local_event[0][2] = 0.8
    action = controller.act(local_event)

    assert controller.architecture == "local_rows_independent_per_vsg_md_actions"
    assert action.shape == (4, 2)
    np.testing.assert_allclose(action[0], [0.25, 0.25], rtol=0.0, atol=1e-7)
    np.testing.assert_array_equal(action[1:], np.zeros((3, 2)))


def test_local_law_is_disturbance_sign_symmetric_and_ignores_power_setpoint() -> None:
    contract = LocalNeighbourMDContract(inertia_gain=1.0, damping_gain=1.0)
    original = {actor: np.zeros(7, dtype=np.float32) for actor in range(4)}
    original[0] = np.asarray([0.2, 0.3, -0.4, -0.1, 0.2, 0.1, -0.2])
    inverted = {actor: row.copy() for actor, row in original.items()}
    inverted[0][1:] *= -1.0
    changed_power = {actor: row.copy() for actor, row in original.items()}
    changed_power[0][0] = 1.9
    changed_nonlocal = {actor: row.copy() for actor, row in original.items()}
    changed_nonlocal[2][1:] = 100.0

    reference = LocalNeighbourMDExecution(contract).act(original)
    sign_inverted = LocalNeighbourMDExecution(contract).act(inverted)
    power_changed = LocalNeighbourMDExecution(contract).act(changed_power)
    nonlocal_changed = LocalNeighbourMDExecution(contract).act(changed_nonlocal)

    np.testing.assert_array_equal(sign_inverted[0], reference[0])
    np.testing.assert_array_equal(power_changed[0], reference[0])
    np.testing.assert_array_equal(nonlocal_changed[0], reference[0])


def test_slew_bounds_and_reset_are_owned_independently_by_each_vsg_agent() -> None:
    controller = LocalNeighbourMDExecution(
        LocalNeighbourMDContract(inertia_gain=2.0, damping_gain=2.0)
    )
    event = {actor: np.zeros(7, dtype=np.float32) for actor in range(4)}
    event[0][1:3] = [1.0, 1.0]

    first = controller.act(event)
    second = controller.act(event)
    assert np.max(np.abs(second - first)) <= 0.25
    assert np.max(np.abs(second)) <= 1.0
    assert not np.array_equal(controller.agents[0].previous_action, controller.agents[1].previous_action)

    controller.reset()
    restarted = controller.act(event)
    np.testing.assert_array_equal(restarted, first)


def test_shared_action_projection_seam_is_rowwise_and_reusable_by_future_marl() -> None:
    projector = PerVSGMDActionProjector(action_slew_limit=0.25)
    targets = np.asarray(
        [[1.0, -1.0], [0.5, 0.5], [0.0, 0.0], [-0.5, 0.5]],
        dtype=np.float32,
    )

    first = projector.project(targets)
    second = projector.project(targets)
    np.testing.assert_array_equal(
        first,
        [[0.25, -0.25], [0.25, 0.25], [0.0, 0.0], [-0.25, 0.25]],
    )
    np.testing.assert_array_equal(
        second,
        [[0.5, -0.5], [0.5, 0.5], [0.0, 0.0], [-0.5, 0.5]],
    )

    projector.reset()
    np.testing.assert_array_equal(projector.project(targets), first)
