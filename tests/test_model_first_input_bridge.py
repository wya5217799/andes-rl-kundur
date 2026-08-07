from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation.model_first_dynamic_reduction import (
    simulate_state_space,
)
from andes_rl_kundur.evaluation.model_first_input_bridge import (
    fit_normalized_era_realization,
    fold_zero_time_constant_states,
    post_step_sampled_realization,
    reduce_folded_descriptor,
)


def _markov_from_realization(realization, steps: int) -> np.ndarray:
    inputs = np.zeros((steps, realization.input_matrix.shape[1]))
    outputs = []
    for column in range(inputs.shape[1]):
        impulse = inputs.copy()
        impulse[0, column] = 1.0
        outputs.append(simulate_state_space(realization, impulse))
    return np.stack(outputs, axis=2)


def test_zero_time_constant_states_are_folded_into_the_algebraic_block() -> None:
    tf = np.asarray([2.0, 0.0, 3.0])
    fx = np.asarray(
        [
            [-2.0, 0.5, 0.1],
            [0.4, -4.0, 0.2],
            [0.3, 0.6, -3.0],
        ]
    )
    fy = np.asarray([[1.0], [2.0], [-1.0]])
    gx = np.asarray([[0.7, -0.2, 0.9]])
    gy = np.asarray([[5.0]])
    f_input = np.asarray([[1.0, 0.0], [0.5, -1.0], [0.0, 2.0]])
    g_input = np.asarray([[0.25, -0.75]])

    folded = fold_zero_time_constant_states(
        time_constants=tf,
        f_x=fx,
        f_y=fy,
        g_x=gx,
        g_y=gy,
        f_input=f_input,
        g_input=g_input,
    )

    np.testing.assert_array_equal(folded.dynamic_state_indices, [0, 2])
    np.testing.assert_array_equal(folded.folded_state_indices, [1])
    np.testing.assert_allclose(folded.e_d, np.diag([2.0, 3.0]))
    np.testing.assert_allclose(folded.f_x, fx[np.ix_([0, 2], [0, 2])])
    np.testing.assert_allclose(
        folded.f_algebraic,
        np.asarray([[1.0, 0.5], [-1.0, 0.6]]),
    )
    np.testing.assert_allclose(
        folded.g_x,
        np.asarray([[0.7, 0.9], [0.4, 0.2]]),
    )
    np.testing.assert_allclose(
        folded.g_algebraic,
        np.asarray([[5.0, -0.2], [2.0, -4.0]]),
    )
    np.testing.assert_allclose(folded.f_input, f_input[[0, 2]])
    np.testing.assert_allclose(
        folded.g_input,
        np.vstack([g_input, f_input[[1]]]),
    )


def test_folded_descriptor_reduction_matches_direct_block_elimination() -> None:
    folded = fold_zero_time_constant_states(
        time_constants=np.asarray([2.0, 0.0, 3.0]),
        f_x=np.asarray(
            [
                [-2.0, 0.5, 0.1],
                [0.4, -4.0, 0.2],
                [0.3, 0.6, -3.0],
            ]
        ),
        f_y=np.asarray([[1.0], [2.0], [-1.0]]),
        g_x=np.asarray([[0.7, -0.2, 0.9]]),
        g_y=np.asarray([[5.0]]),
        f_input=np.asarray([[1.0], [0.5], [0.0]]),
        g_input=np.asarray([[0.25]]),
    )

    reduced = reduce_folded_descriptor(folded, minimum_reciprocal_condition=1e-12)

    expected_rhs_a = folded.f_x - folded.f_algebraic @ np.linalg.solve(
        folded.g_algebraic, folded.g_x
    )
    expected_rhs_b = folded.f_input - folded.f_algebraic @ np.linalg.solve(
        folded.g_algebraic, folded.g_input
    )
    np.testing.assert_allclose(
        reduced.state_matrix,
        np.linalg.solve(folded.e_d, expected_rhs_a),
    )
    np.testing.assert_allclose(
        reduced.input_matrix,
        np.linalg.solve(folded.e_d, expected_rhs_b),
    )
    assert reduced.algebraic_reciprocal_condition > 1e-12


def test_post_step_sampling_matches_end_of_hold_observations() -> None:
    continuous_a = np.asarray([[-2.0]])
    continuous_b = np.asarray([[3.0]])
    continuous_c = np.asarray([[5.0]])
    continuous_d = np.asarray([[0.25]])

    sampled = post_step_sampled_realization(
        state_matrix=continuous_a,
        input_matrix=continuous_b,
        output_matrix=continuous_c,
        feedthrough_matrix=continuous_d,
        sample_period_seconds=0.2,
    )

    expected_a = np.exp(-0.4)
    expected_b = 3.0 * (1.0 - expected_a) / 2.0
    np.testing.assert_allclose(sampled.state_matrix, [[expected_a]])
    np.testing.assert_allclose(sampled.input_matrix, [[expected_b]])
    np.testing.assert_allclose(sampled.output_matrix, [[5.0 * expected_a]])
    np.testing.assert_allclose(
        sampled.feedthrough_matrix,
        [[5.0 * expected_b + 0.25]],
    )

    impulse = np.asarray([[1.0], [0.0], [0.0]])
    response = simulate_state_space(sampled, impulse)[:, 0]
    np.testing.assert_allclose(
        response,
        [5.0 * expected_b + 0.25, 5.0 * expected_a * expected_b, 5.0 * expected_a**2 * expected_b],
    )


def test_normalized_era_returns_a_model_in_original_physical_units() -> None:
    continuous = post_step_sampled_realization(
        state_matrix=np.diag([-1.0, -2.0]),
        input_matrix=np.asarray([[1.0, 0.5], [0.25, 1.5]]),
        output_matrix=np.asarray([[1.0, -0.5], [0.2, 1.0]]),
        feedthrough_matrix=np.zeros((2, 2)),
        sample_period_seconds=0.2,
    )
    physical_markov = _markov_from_realization(continuous, 12)

    fitted = fit_normalized_era_realization(
        physical_markov,
        input_scales=np.asarray([0.5, 2.0]),
        output_scales=np.asarray([4.0, 0.25]),
        order=2,
        block_rows=4,
        block_columns=4,
    )

    fitted_markov = _markov_from_realization(fitted, 12)
    np.testing.assert_allclose(fitted_markov, physical_markov, atol=1e-11)


def test_input_normalization_requires_one_positive_scale_per_channel() -> None:
    markov = np.ones((8, 2, 2))

    for invalid in (np.asarray([1.0]), np.asarray([1.0, 0.0])):
        try:
            fit_normalized_era_realization(
                markov,
                input_scales=invalid,
                output_scales=np.ones(2),
                order=1,
                block_rows=2,
                block_columns=2,
            )
        except ValueError as exc:
            assert "input_scales" in str(exc)
        else:
            raise AssertionError("invalid input scales were accepted")
