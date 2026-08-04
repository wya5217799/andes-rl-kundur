import numpy as np

from andes_rl_kundur.control.active_power import PowerProjection
from andes_rl_kundur.control.coupling_aware_power import DistributedDAPIController
from andes_rl_kundur.control.decentralized_dapi import DecentralizedDAPIExecution


RING = {0: [1, 3], 1: [0, 2], 2: [1, 3], 3: [2, 0]}


def _controllers():
    common = {
        "adjacency": RING,
        "device_count": 4,
        "nominal_frequency_hz": 60.0,
        "kp_system_pu_per_hz_per_device": 2.0,
        "ki_system_pu_per_hz_s_per_device": 0.2,
        "sync_gain_system_pu_per_hz": 1.0,
        "consensus_gain_per_s": 1.0,
    }
    return DistributedDAPIController(**common), DecentralizedDAPIExecution(**common)


def test_explicit_local_agents_are_stepwise_equivalent_to_sparse_vector_law():
    vector, local = _controllers()
    rng = np.random.default_rng(294)
    previous = None
    for step in range(30):
        frequency = 60.0 + rng.normal(0.0, 0.08, size=4)
        if step % 4 == 0:
            requested = rng.normal(0.0, 0.5, size=4)
            commanded = np.clip(requested, -0.2, 0.2)
            previous = PowerProjection(
                requested_power_system_pu=requested,
                commanded_power_system_pu=commanded,
                saturation_reasons=((),) * 4,
            )
        expected = vector.act(
            frequencies_hz=frequency,
            dt_seconds=0.2,
            previous_projection=previous,
        )
        observed = local.act(
            frequencies_hz=frequency,
            dt_seconds=0.2,
            previous_projection=previous,
        )
        np.testing.assert_allclose(observed, expected, rtol=0.0, atol=1e-13)


def test_each_local_agent_has_independent_state_and_scalar_output_contract():
    _, local = _controllers()
    assert len({id(agent) for agent in local.agents}) == 4
    assert [agent.neighbour_ids for agent in local.agents] == [
        (1, 3),
        (0, 2),
        (1, 3),
        (2, 0),
    ]
    output = local.act(frequencies_hz=[59.9, 60.0, 60.2, 60.0], dt_seconds=0.2)
    assert output.shape == (4,)
    assert not np.allclose(output, output[0])
