from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import torch

from andes_rl_kundur.agents.classical_prior_td3 import (
    CentralPriorResidualTD3,
    DistributedPriorResidualTD3,
)
from andes_rl_kundur.control.classical_edge_residual import (
    ClassicalEdgeContract,
    classical_edge_candidates,
    classical_raw_edge,
    compose_prior_residual_numpy,
    edge_severity_delta,
)
from andes_rl_kundur.control.vector_inertia_residual import (
    execute_edge_residual_numpy,
)
from andes_rl_kundur.evaluation.vector_residual import (
    residual_composition_telemetry,
)


def _observations() -> dict[int, np.ndarray]:
    values = (
        (0.2, -1.0, 0.0, 0.5, 1.0),
        (0.1, -0.2, 0.0, 0.1, 1.0),
        (-0.3, 0.4, 0.0, -0.2, -1.0),
        (-0.1, 0.1, 0.0, -0.1, -1.0),
    )
    return {
        index: np.asarray(value, dtype=np.float32)
        for index, value in enumerate(values)
    }


def test_frozen_classical_family_has_nine_unique_local_candidates() -> None:
    candidates = classical_edge_candidates()

    assert len(candidates) == 9
    assert len({candidate.name for candidate in candidates}) == 9
    assert {candidate.family for candidate in candidates} == {
        "rocof",
        "freq_rocof",
        "full",
    }
    assert {candidate.gain for candidate in candidates} == {0.25, 0.5, 1.0}


def test_classical_flow_moves_inertia_toward_more_severe_endpoint() -> None:
    contract = ClassicalEdgeContract(family="rocof", gain=1.0)
    observations = _observations()

    raw = classical_raw_edge(observations, contract)
    edge, node, _actions = execute_edge_residual_numpy(
        raw,
        previous_edge=np.zeros(3, dtype=np.float32),
        step=0,
    )

    assert raw[0] < 0.0
    assert edge[0] < 0.0
    assert node[0] > 0.0
    assert node[1] < 0.0


def test_severity_law_is_sign_symmetric_and_strictly_edge_local() -> None:
    contract = ClassicalEdgeContract(family="full", gain=0.5)
    original = _observations()
    inverted = {
        index: value * np.asarray([-1, -1, 1, -1, 1], dtype=np.float32)
        for index, value in original.items()
    }
    changed_nonendpoint = {index: value.copy() for index, value in original.items()}
    changed_nonendpoint[2][:4] += 100.0
    changed_nonendpoint[3][:4] -= 100.0

    first = classical_raw_edge(original, contract)
    sign_inverted = classical_raw_edge(inverted, contract)
    nonendpoint_changed = classical_raw_edge(changed_nonendpoint, contract)

    np.testing.assert_array_equal(first, sign_inverted)
    assert first[0] == nonendpoint_changed[0]


def test_neural_residual_changes_magnitude_but_cannot_reverse_prior() -> None:
    delta = np.asarray([-0.8, 0.3, 0.0], dtype=np.float32)
    prior = np.tanh(delta).astype(np.float32)

    reduced = compose_prior_residual_numpy(
        prior,
        np.full(3, -1.0, dtype=np.float32),
        delta,
    )
    increased = compose_prior_residual_numpy(
        prior,
        np.full(3, 1.0, dtype=np.float32),
        delta,
    )

    assert reduced[0] <= 0.0 and increased[0] <= 0.0
    assert reduced[1] >= 0.0 and increased[1] >= 0.0
    assert abs(increased[0]) >= abs(reduced[0])
    assert abs(increased[1]) >= abs(reduced[1])
    assert reduced[2] == 0.0 and increased[2] == 0.0


def test_beta_zero_is_exactly_the_existing_magnitude_only_projection() -> None:
    delta = np.asarray([-0.8, 0.3, 0.0], dtype=np.float32)
    prior = np.tanh(delta).astype(np.float32)
    residual = np.asarray([-0.7, 0.4, -1.0], dtype=np.float32)
    expected = np.sign(delta) * np.clip(
        np.abs(prior) + np.float32(0.5) * np.clip(residual, -1.0, 1.0),
        0.0,
        1.0,
    )

    actual = compose_prior_residual_numpy(
        prior,
        residual,
        delta,
        reverse_limit=0.0,
    )

    np.testing.assert_array_equal(actual, expected.astype(np.float32))


def test_limited_reverse_is_bounded_and_classical_prior_remains_nested() -> None:
    delta = np.asarray([-0.1, 0.1, 0.0], dtype=np.float32)
    prior = np.tanh(delta).astype(np.float32)
    reverse = compose_prior_residual_numpy(
        prior,
        np.full(3, -1.0, dtype=np.float32),
        delta,
        reverse_limit=0.1,
    )
    classical = compose_prior_residual_numpy(
        prior,
        np.zeros(3, dtype=np.float32),
        delta,
        reverse_limit=0.1,
    )

    np.testing.assert_allclose(
        np.sign(delta[:2]) * reverse[:2],
        np.full(2, -0.1, dtype=np.float32),
        rtol=0.0,
        atol=1e-7,
    )
    np.testing.assert_array_equal(classical, prior)
    assert reverse[2] == 0.0


def test_reverse_limit_contract_identity_validation_and_tensor_parity() -> None:
    with pytest.raises(ValueError, match="reverse_limit"):
        ClassicalEdgeContract(family="full", gain=1.0, reverse_limit=-0.1)
    with pytest.raises(ValueError, match="reverse_limit"):
        ClassicalEdgeContract(family="full", gain=1.0, reverse_limit=1.1)

    contract = ClassicalEdgeContract(
        family="full",
        gain=1.0,
        residual_scale=0.5,
        reverse_limit=0.1,
    )
    assert contract.name == "classical_edge_full_k1_b0p1"
    observations = _observations()
    residual = np.asarray([-1.0, 0.25, -0.75], dtype=np.float32)
    agent = DistributedPriorResidualTD3(classical_contract=contract)
    numpy_action = agent.compose_actor_residual(observations, residual)
    joint = torch.as_tensor(
        np.concatenate([observations[index] for index in range(4)]).reshape(1, -1),
        dtype=torch.float32,
    )
    tensor_action = agent._compose_tensor(
        joint,
        torch.as_tensor(residual.reshape(1, 3), dtype=torch.float32),
    ).detach().cpu().numpy().reshape(3)

    np.testing.assert_allclose(tensor_action, numpy_action, rtol=0.0, atol=1e-7)


def test_limited_reverse_telemetry_records_mechanism_without_changing_action() -> None:
    contract = ClassicalEdgeContract(
        family="full",
        gain=1.0,
        reverse_limit=0.1,
    )
    agent = DistributedPriorResidualTD3(classical_contract=contract)
    observations = _observations()
    residual = np.full(3, -1.0, dtype=np.float32)

    action = agent.compose_actor_residual(observations, residual)
    telemetry = residual_composition_telemetry(agent)

    assert telemetry is not None
    np.testing.assert_array_equal(
        np.asarray(telemetry["executed_edge_action"], dtype=np.float32),
        action,
    )
    aligned = np.asarray(telemetry["aligned_magnitude"], dtype=np.float32)
    assert telemetry["reverse_count"] == int(np.sum(aligned < 0.0))
    assert telemetry["reverse_limit"] == 0.1
    assert all(value >= -0.1 - 1e-7 for value in aligned)


def test_prior_residual_agents_preserve_locality_capacity_and_checkpoint(
    tmp_path: Path,
) -> None:
    contract = ClassicalEdgeContract(family="freq_rocof", gain=0.5)
    torch.manual_seed(293)
    distributed = DistributedPriorResidualTD3(classical_contract=contract)
    central = CentralPriorResidualTD3(classical_contract=contract)
    original = _observations()
    changed = {index: value.copy() for index, value in original.items()}
    changed[2][:4] += 100.0
    changed[3][:4] -= 100.0

    first = distributed.select_edge_actions(original, deterministic=True)
    second = distributed.select_edge_actions(changed, deterministic=True)
    assert first[0] == second[0]

    distributed_count = sum(p.numel() for p in distributed.actor.parameters())
    central_count = sum(p.numel() for p in central.actor.parameters())
    assert distributed_count == 4929
    assert central_count == 4959
    assert abs(central_count - distributed_count) / distributed_count < 0.01

    checkpoint = tmp_path / "prior.pt"
    distributed.save(checkpoint, metadata={"round": "R293"})
    restored = DistributedPriorResidualTD3(classical_contract=contract)
    metadata = restored.load(checkpoint)
    assert metadata == {"round": "R293"}
    np.testing.assert_array_equal(
        first,
        restored.select_edge_actions(original, deterministic=True),
    )


def test_equal_endpoint_severity_forces_zero_edge_action() -> None:
    observations = _observations()
    observations[1] = observations[0].copy()
    contract = ClassicalEdgeContract(family="full", gain=1.0)

    delta = edge_severity_delta(observations, contract)
    raw = classical_raw_edge(observations, contract)

    assert delta[0] == 0.0
    assert raw[0] == 0.0
