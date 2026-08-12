from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from andes_rl_kundur.env.andes.model_first_contract import (
    ModelFirstConfig,
    active_power_incidence,
    descriptor_schur_complement,
    device_to_system_base,
    finite_difference_input_jacobians,
    stage1_operating_points,
    stage1_power_coordinates,
    transform_linear_blocks,
    weighted_common_differential_transform,
)


def test_model_first_config_freezes_physical_plant_without_v4_mutation() -> None:
    config = ModelFirstConfig()

    assert config.physical_nominal_frequency_hz == 60.0
    assert config.zero_g4_inertia is False
    assert config.disable_default_toggler is True
    assert config.random_disturbance is False
    assert config.comm_fail_probability == 0.0
    np.testing.assert_allclose(config.vsg_m_system, np.full(4, 400.0))
    np.testing.assert_allclose(config.vsg_d_system, np.full(4, 200.0))


def test_device_to_system_base_applies_sn_over_ssys_exactly_once() -> None:
    values = device_to_system_base(
        [200.0, 100.0],
        device_mva=200.0,
        system_mva=100.0,
    )

    np.testing.assert_allclose(values, [400.0, 200.0], atol=0.0)


def test_active_power_incidence_has_frozen_signs_rank_and_neutrality() -> None:
    incidence = active_power_incidence()

    np.testing.assert_array_equal(
        incidence,
        np.asarray(
            [
                [1.0, 0.0, 0.0],
                [-1.0, 1.0, 0.0],
                [0.0, -1.0, 1.0],
                [0.0, 0.0, -1.0],
            ]
        ),
    )
    assert np.linalg.matrix_rank(incidence) == 3
    np.testing.assert_array_equal(np.ones(4) @ incidence, np.zeros(3))


def test_weighted_coordinate_map_is_exact_and_uses_the_frozen_common_mode() -> None:
    inertia = np.diag([400.0, 300.0, 500.0, 200.0])
    transform = weighted_common_differential_transform(inertia)
    omega = np.asarray([0.01, -0.02, 0.03, 0.04])

    np.testing.assert_allclose(transform.q.T @ transform.q, np.eye(4), atol=1e-12)
    np.testing.assert_allclose(
        transform.q[:, 0],
        np.sqrt(np.diag(inertia)) / np.sqrt(np.sum(np.diag(inertia))),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        transform.inverse @ transform.forward,
        np.eye(4),
        atol=1e-12,
    )
    np.testing.assert_allclose(
        transform.inverse @ (transform.forward @ omega),
        omega,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        transform.forward[0] @ omega,
        np.sqrt(np.sum(np.diag(inertia)))
        * (np.diag(inertia) @ omega).sum()
        / np.sum(np.diag(inertia)),
        atol=1e-12,
    )


def test_transformed_blocks_reconstruct_the_original_without_dropping_cross_terms() -> None:
    inertia = np.diag([4.0, 3.0, 5.0, 2.0])
    coordinates = weighted_common_differential_transform(inertia)
    state_matrix = np.asarray(
        [
            [-1.0, 0.4, 0.0, 0.1],
            [0.2, -2.0, 0.3, 0.0],
            [0.0, 0.1, -3.0, 0.5],
            [0.6, 0.0, 0.2, -4.0],
        ]
    )
    input_matrix = np.arange(16.0).reshape(4, 4) / 10.0

    blocks = transform_linear_blocks(
        state_matrix,
        input_matrix,
        state_forward=coordinates.forward,
        state_inverse=coordinates.inverse,
        input_forward=coordinates.forward,
        input_inverse=coordinates.inverse,
    )

    np.testing.assert_allclose(blocks.reconstructed_state, state_matrix, atol=1e-12)
    np.testing.assert_allclose(blocks.reconstructed_input, input_matrix, atol=1e-12)
    assert np.linalg.norm(blocks.a_cd) > 0.0
    assert np.linalg.norm(blocks.a_dc) > 0.0
    assert np.linalg.norm(blocks.b_cd) > 0.0
    assert np.linalg.norm(blocks.b_dc) > 0.0


def test_descriptor_schur_complement_matches_direct_elimination() -> None:
    e_d = np.diag([2.0, 3.0])
    f_x = np.asarray([[-2.0, 0.5], [0.25, -1.0]])
    f_y = np.asarray([[1.0], [2.0]])
    g_x = np.asarray([[0.5, -0.25]])
    g_y = np.asarray([[4.0]])
    f_p = np.asarray([[1.0], [0.0]])
    g_p = np.asarray([[2.0]])
    f_rho = np.asarray([[0.0], [3.0]])
    g_rho = np.asarray([[1.5]])
    e_d_rho = np.asarray([[0.2, 0.0], [0.0, -0.1]])
    x_dot = np.asarray([0.5, -0.25])

    reduced = descriptor_schur_complement(
        e_d=e_d,
        f_x=f_x,
        f_y=f_y,
        g_x=g_x,
        g_y=g_y,
        f_p=f_p,
        g_p=g_p,
        f_rho=f_rho,
        g_rho=g_rho,
        e_d_rho=e_d_rho,
        x_dot=x_dot,
    )

    solve_gx = np.linalg.solve(g_y, g_x)
    np.testing.assert_allclose(reduced.a, f_x - f_y @ solve_gx)
    np.testing.assert_allclose(
        reduced.b_p,
        f_p - f_y @ np.linalg.solve(g_y, g_p),
    )
    np.testing.assert_allclose(
        reduced.b_rho,
        f_rho
        - f_y @ np.linalg.solve(g_y, g_rho)
        - e_d_rho @ x_dot[:, None],
    )
    np.testing.assert_allclose(reduced.e_d, e_d)


def test_finite_difference_input_jacobians_recover_descriptor_input_blocks() -> None:
    f_input = np.asarray([[2.0, -1.0], [0.5, 3.0]])
    g_input = np.asarray([[4.0, -2.0]])

    def residual(command: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        nonlinear = np.asarray([command[0] ** 2, command[1] ** 2])
        return f_input @ command + nonlinear, g_input @ command

    jacobians = finite_difference_input_jacobians(
        residual,
        equilibrium_input=np.zeros(2),
        step=1e-6,
    )

    np.testing.assert_allclose(jacobians.f_input, f_input, atol=1e-10)
    np.testing.assert_allclose(jacobians.g_input, g_input, atol=1e-10)
    np.testing.assert_allclose(
        jacobians.midpoint_ratios,
        np.asarray([1e-6 / 4.5, 1e-6 / np.sqrt(14.0)]),
    )
    assert jacobians.scheme == "central"


def test_stage1_contract_exposes_only_the_frozen_points_and_power_coordinates() -> None:
    points = stage1_operating_points()
    coordinates = stage1_power_coordinates()

    assert [point.name for point in points] == ["OP0", "OP1", "OP2"]
    assert [
        (
            point.vsg_m_device,
            point.vsg_d_device,
            point.vsg_m_system,
            point.vsg_d_system,
            point.tie_rx_scale,
            point.initial_soc,
        )
        for point in points
    ] == [
        (200.0, 100.0, 400.0, 200.0, 1.0, 0.5),
        (150.0, 75.0, 300.0, 150.0, 1.0, 0.3),
        (250.0, 125.0, 500.0, 250.0, 2.0, 0.7),
    ]
    assert list(coordinates) == ["common", "edge_0", "edge_1", "edge_2"]
    np.testing.assert_array_equal(coordinates["common"], np.full(4, 0.05))
    np.testing.assert_array_equal(
        np.column_stack([coordinates[f"edge_{index}"] for index in range(3)]),
        0.05 * active_power_incidence(),
    )
    assert all(float(np.sum(coordinates[f"edge_{index}"])) == 0.0 for index in range(3))


def test_stage1_power_coordinates_scale_an_unseen_holdout_amplitude() -> None:
    coordinates = stage1_power_coordinates(0.025)

    np.testing.assert_array_equal(coordinates["common"], np.full(4, 0.025))
    np.testing.assert_array_equal(
        coordinates["edge_0"], np.asarray([0.025, -0.025, 0.0, 0.0])
    )
    with pytest.raises(ValueError, match="positive and finite"):
        stage1_power_coordinates(0.0)


def test_model_first_config_materializes_one_stage1_operating_point() -> None:
    point = stage1_operating_points()[2]

    config = ModelFirstConfig.for_stage1_operating_point(point)

    assert config.vsg_m_device == (250.0, 250.0, 250.0, 250.0)
    assert config.vsg_d_device == (125.0, 125.0, 125.0, 125.0)
    np.testing.assert_array_equal(config.vsg_m_system, np.full(4, 500.0))
    np.testing.assert_array_equal(config.vsg_d_system, np.full(4, 250.0))
    assert config.tie_rx_scale == 2.0
    assert config.initial_soc == 0.7


def test_model_first_config_exposes_one_optional_strict_tds_contract() -> None:
    point = stage1_operating_points()[1]

    legacy = ModelFirstConfig.for_stage1_operating_point(point)
    strict = replace(legacy, tds_convergence_tolerance=1e-10)

    assert legacy.tds_convergence_tolerance is None
    assert legacy.tds_tiny_correction_threshold is None
    assert strict.tds_convergence_tolerance == 1e-10
    assert strict.tds_tiny_correction_threshold == 1e-16


def test_model_first_config_exposes_distinct_post_initialization_tds_contract() -> None:
    point = stage1_operating_points()[1]

    config = replace(
        ModelFirstConfig.for_stage1_operating_point(point),
        tds_post_initialization_convergence_tolerance=1e-10,
    )

    assert config.tds_convergence_tolerance is None
    assert config.tds_post_initialization_convergence_tolerance == 1e-10
    assert config.tds_post_initialization_tiny_correction_threshold == 1e-16


def test_model_first_config_rejects_ambiguous_two_tds_contracts() -> None:
    with pytest.raises(ValueError, match="cannot both be set"):
        ModelFirstConfig(
            tds_convergence_tolerance=1e-8,
            tds_post_initialization_convergence_tolerance=1e-10,
        )


@pytest.mark.parametrize("value", [0.0, -1e-10, float("nan"), float("inf")])
def test_model_first_config_rejects_invalid_tds_tolerances(value: float) -> None:
    with pytest.raises(ValueError, match="tds_convergence_tolerance"):
        ModelFirstConfig(tds_convergence_tolerance=value)

    with pytest.raises(
        ValueError,
        match="tds_post_initialization_convergence_tolerance",
    ):
        ModelFirstConfig(tds_post_initialization_convergence_tolerance=value)
