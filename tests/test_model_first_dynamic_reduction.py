import numpy as np
import pytest

from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    StateSpaceRealization,
    enforce_spectral_radius,
    fit_era_realization,
    realization_from_dict,
    realization_to_dict,
    recover_markov_parameters,
    simulate_fir_response,
    simulate_mimo_fir_response,
    simulate_state_space,
)


def test_recovers_markov_parameters_from_a_finite_rectangular_pulse() -> None:
    pulse_response = np.array(
        [
            [0.4, -0.2],
            [0.6, -0.1],
            [0.1, 0.15],
            [-0.05, 0.075],
        ]
    )

    markov = recover_markov_parameters(
        pulse_response,
        pulse_width_steps=2,
        pulse_amplitude=0.2,
    )

    np.testing.assert_allclose(
        markov,
        [
            [2.0, -1.0],
            [1.0, 0.5],
            [-0.5, 0.25],
            [0.25, 0.125],
        ]
    )


def test_markov_parameters_predict_an_off_template_input_sequence() -> None:
    markov = np.array(
        [
            [2.0, -1.0],
            [1.0, 0.5],
            [-0.5, 0.25],
        ]
    )

    response = simulate_fir_response(markov, [0.1, -0.2, 0.3])

    np.testing.assert_allclose(
        response,
        [
            [0.2, -0.1],
            [-0.3, 0.25],
            [0.35, -0.375],
        ]
    )


def test_mimo_markov_tensor_superposes_input_channels() -> None:
    markov = np.array(
        [
            [[1.0, 2.0], [0.0, -1.0]],
            [[0.5, 0.0], [1.0, 0.0]],
        ]
    )
    inputs = np.array([[1.0, 0.5], [-1.0, 0.0], [0.0, 1.0]])

    response = simulate_mimo_fir_response(markov, inputs)

    np.testing.assert_allclose(
        response,
        [
            [2.0, -0.5],
            [-0.5, 1.0],
            [1.5, -2.0],
        ],
    )


def test_era_recovers_a_known_stable_first_order_system() -> None:
    markov = np.array(
        [[[0.1]], [[2.0]], [[1.6]], [[1.28]], [[1.024]], [[0.8192]], [[0.65536]]]
    )

    realization = fit_era_realization(
        markov,
        order=1,
        block_rows=3,
        block_columns=3,
    )
    response = simulate_state_space(
        realization,
        np.array([[1.0], [0.0], [0.0], [0.0], [0.0], [0.0], [0.0]]),
    )

    assert realization.spectral_radius == pytest.approx(0.8)
    np.testing.assert_allclose(response[:, 0], markov[:, 0, 0], atol=1e-12)


def test_spectral_projection_clips_only_unstable_poles() -> None:
    realization = StateSpaceRealization(
        state_matrix=np.diag([1.02, 0.9]),
        input_matrix=np.ones((2, 1)),
        output_matrix=np.ones((1, 2)),
        feedthrough_matrix=np.zeros((1, 1)),
        retained_singular_values=np.array([2.0, 1.0]),
    )

    stabilized = enforce_spectral_radius(realization, maximum_radius=0.995)

    assert stabilized.spectral_radius == pytest.approx(0.995)
    np.testing.assert_allclose(np.linalg.eigvals(stabilized.state_matrix), [0.995, 0.9])
    np.testing.assert_allclose(stabilized.input_matrix, realization.input_matrix)
    np.testing.assert_allclose(stabilized.output_matrix, realization.output_matrix)


def test_realization_json_round_trip_preserves_the_frozen_model() -> None:
    realization = StateSpaceRealization(
        state_matrix=np.array([[0.8, 0.1], [0.0, 0.7]]),
        input_matrix=np.array([[1.0, 0.0], [0.2, 1.0]]),
        output_matrix=np.array([[1.0, -0.5], [0.0, 2.0]]),
        feedthrough_matrix=np.array([[0.1, 0.0], [0.0, -0.2]]),
        retained_singular_values=np.array([3.0, 1.5]),
    )

    restored = realization_from_dict(realization_to_dict(realization))

    np.testing.assert_allclose(restored.state_matrix, realization.state_matrix)
    np.testing.assert_allclose(restored.input_matrix, realization.input_matrix)
    np.testing.assert_allclose(restored.output_matrix, realization.output_matrix)
    np.testing.assert_allclose(
        restored.feedthrough_matrix, realization.feedthrough_matrix
    )
    np.testing.assert_allclose(
        restored.retained_singular_values, realization.retained_singular_values
    )
