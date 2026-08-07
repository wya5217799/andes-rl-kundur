"""Analytic tests for a solver-status-independent minimum-norm certificate."""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.minimum_norm_certificate import (
    certify_convex_minimum_norm,
)


def test_certificate_accepts_exact_one_dimensional_boundary_minimum() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.02]),
        constraint_function=lambda value: np.asarray([value[0] - 0.02]),
        feasibility_tolerance=1.0e-8,
    )

    assert certificate.valid, certificate.reason
    assert certificate.feasible
    assert certificate.active_constraint_count == 1
    assert certificate.stationarity_residual <= certificate.optimality_tolerance


def test_certificate_rejects_feasible_but_nonminimum_interior_point() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.03]),
        constraint_function=lambda value: np.asarray([value[0] - 0.02]),
        feasibility_tolerance=1.0e-8,
    )

    assert not certificate.valid
    assert certificate.feasible
    assert certificate.reason == "stationarity-failed"


def test_certificate_rejects_infeasible_point() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.019]),
        constraint_function=lambda value: np.asarray([value[0] - 0.02]),
        feasibility_tolerance=1.0e-8,
    )

    assert not certificate.valid
    assert not certificate.feasible
    assert certificate.reason == "constraint-infeasible"


def test_certificate_accepts_known_two_dimensional_projection() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.5, 0.5]),
        constraint_function=lambda value: np.asarray([value[0] + value[1] - 1.0]),
        feasibility_tolerance=1.0e-8,
    )

    assert certificate.valid, certificate.reason
    np.testing.assert_allclose(certificate.multipliers, np.asarray([1.0]), atol=1.0e-6)


def test_certificate_rejects_active_nonconvex_guard() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.02]),
        constraint_function=lambda value: np.asarray([value[0] - 0.02]),
        feasibility_tolerance=1.0e-8,
        nonconvex_constraint_slacks=np.asarray([0.0]),
    )

    assert not certificate.valid
    assert certificate.reason == "nonconvex-constraint-active"


def test_certificate_rejects_perturbed_boundary_point() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.5002, 0.4998]),
        constraint_function=lambda value: np.asarray([value[0] + value[1] - 1.0]),
        feasibility_tolerance=1.0e-8,
    )

    assert not certificate.valid
    assert certificate.feasible
    assert certificate.reason == "stationarity-failed"


def test_certificate_handles_duplicated_active_constraints() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([0.5, 0.5]),
        constraint_function=lambda value: np.asarray(
            [value[0] + value[1] - 1.0, value[0] + value[1] - 1.0]
        ),
        feasibility_tolerance=1.0e-8,
    )

    assert certificate.valid, certificate.reason
    assert certificate.active_constraint_count == 2


def test_certificate_rejects_large_multiplier_complementarity_error() -> None:
    certificate = certify_convex_minimum_norm(
        point=np.asarray([100.0]),
        constraint_function=lambda value: np.asarray([value[0] - 99.99995]),
        feasibility_tolerance=1.0e-8,
    )

    assert not certificate.valid
    assert certificate.feasible
    assert certificate.reason == "complementarity-failed"


def test_certificate_accepts_nonlinear_convex_ball_projection() -> None:
    center = np.asarray([2.0, 0.0])
    certificate = certify_convex_minimum_norm(
        point=np.asarray([1.0, 0.0]),
        constraint_function=lambda value: np.asarray([1.0 - np.sum((value - center) ** 2)]),
        feasibility_tolerance=1.0e-8,
    )

    assert certificate.valid, certificate.reason
    np.testing.assert_allclose(certificate.multipliers, np.asarray([1.0]), atol=1.0e-6)


def test_certificate_matches_halfspace_projections_across_dimensions_and_scales() -> None:
    generator = np.random.default_rng(348)
    for dimension in (1, 2, 4, 8):
        for boundary in (0.01, 1.0, 100.0):
            normal = generator.normal(size=dimension)
            normal /= np.linalg.norm(normal)
            optimum = boundary * normal

            def constraint(
                value: np.ndarray,
                normal: np.ndarray = normal,
                boundary: float = boundary,
            ) -> np.ndarray:
                return np.asarray([normal @ value - boundary])

            exact = certify_convex_minimum_norm(
                point=optimum,
                constraint_function=constraint,
                feasibility_tolerance=1.0e-8,
            )
            assert exact.valid, (dimension, boundary, exact.reason)

            if dimension == 1:
                perturbed = optimum + np.sign(normal) * max(1.0, boundary) * 1.0e-3
            else:
                tangent = np.zeros(dimension)
                tangent[:2] = np.asarray([-normal[1], normal[0]])
                tangent /= np.linalg.norm(tangent)
                perturbed = optimum + tangent * max(1.0, boundary) * 1.0e-3
            nonminimum = certify_convex_minimum_norm(
                point=perturbed,
                constraint_function=constraint,
                feasibility_tolerance=1.0e-8,
            )
            assert not nonminimum.valid, (dimension, boundary, nonminimum.reason)


@pytest.mark.parametrize(
    ("point", "constraint_function"),
    [
        (np.asarray([np.nan]), lambda value: np.asarray([value[0]])),
        (np.asarray([0.0]), lambda _value: np.asarray([[0.0]])),
        (np.asarray([0.0]), lambda _value: np.asarray([np.inf])),
    ],
)
def test_certificate_rejects_invalid_inputs(
    point: np.ndarray,
    constraint_function: object,
) -> None:
    with pytest.raises(ValueError):
        certify_convex_minimum_norm(
            point=point,
            constraint_function=constraint_function,
            feasibility_tolerance=1.0e-8,
        )
