from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.evaluation.model_validation import (
    compare_coordinate_responses,
    coupling_ratios,
    helmert_coordinates,
    multilinear_interpolate,
    multilinear_weights,
)


def test_helmert_coordinates_are_orthonormal_and_differential() -> None:
    transform = helmert_coordinates(4)
    np.testing.assert_allclose(transform @ transform.T, np.eye(4), atol=1e-12)
    np.testing.assert_allclose(transform[1:] @ np.ones(4), 0.0, atol=1e-12)
    np.testing.assert_allclose(transform[0], np.ones(4) / 2.0, atol=1e-12)


def test_multilinear_weights_cover_every_corner_and_sum_to_one() -> None:
    bounds = {"x": (0.0, 2.0), "y": (10.0, 14.0)}
    point = {"x": 0.5, "y": 13.0}
    weights = multilinear_weights(point, bounds, ("x", "y"))
    assert set(weights) == {
        (0.0, 10.0),
        (0.0, 14.0),
        (2.0, 10.0),
        (2.0, 14.0),
    }
    assert sum(weights.values()) == pytest.approx(1.0)


def test_multilinear_interpolation_reproduces_bilinear_matrix() -> None:
    bounds = {"x": (0.0, 2.0), "y": (0.0, 4.0)}
    corners = {
        (x, y): np.asarray([[1.0 + 2.0 * x + 3.0 * y + x * y]])
        for x in bounds["x"]
        for y in bounds["y"]
    }
    got = multilinear_interpolate(
        corners,
        {"x": 0.5, "y": 3.0},
        bounds,
        ("x", "y"),
    )
    np.testing.assert_allclose(got, [[1.0 + 1.0 + 9.0 + 1.5]])


def test_coupling_ratio_and_identical_response_comparison() -> None:
    response = np.zeros((3, 4, 4), dtype=float)
    response[1:, 0, 0] = 2.0
    response[1:, 1:, 1:] = np.eye(3)
    response[1:, 1, 0] = 0.5
    response[1:, 0, 1] = 0.25
    ratios = coupling_ratios(response)
    assert ratios["differential_from_common"] == pytest.approx(0.25)
    assert ratios["common_from_differential"] > 0.0
    comparison = compare_coordinate_responses(response, response.copy())
    assert comparison["response_nrmse"] == 0.0
    assert max(comparison["coupling_absolute_error"].values()) == 0.0
