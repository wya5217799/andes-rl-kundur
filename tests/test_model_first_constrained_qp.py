"""Behavior tests for the prospective sparse constrained-QP solver seam."""

from __future__ import annotations

import numpy as np
import pytest
from scripts.run_r325_constrained_horizon import (
    _designs,
    _load_parent,
    _models,
    development_cases,
)

from andes_rl_kundur.control.model_first_constrained_horizon import (
    ConstrainedHorizonInfeasible,
    simulate_constrained_horizon_feedback,
)


def _sealed_failure_fixture():
    parent, _, _, _ = _load_parent()
    retained, _ = _models(parent)
    case = development_cases()[0]
    designs, feasible, error = _designs({case.point: retained[case.point]})
    assert feasible, error
    return retained[case.point], designs[case.point], case


def test_legacy_solver_reproduces_the_sealed_development_failure() -> None:
    plant, design, case = _sealed_failure_fixture()

    with pytest.raises(ConstrainedHorizonInfeasible, match=r"step 6 .* failed"):
        simulate_constrained_horizon_feedback(
            plant,
            case.disturbance[:7],
            design=design,
            initial_soc=case.initial_soc,
        )


def test_sparse_solver_completes_the_same_failure_prefix() -> None:
    from andes_rl_kundur.control.model_first_constrained_qp import (
        simulate_sparse_constrained_horizon_feedback,
    )

    plant, design, case = _sealed_failure_fixture()
    trace = simulate_sparse_constrained_horizon_feedback(
        plant,
        case.disturbance[:7],
        design=design,
        initial_soc=case.initial_soc,
    )

    assert trace.base.solver_failure_count == 0
    assert trace.base.constraint_violation_count == 0
    assert trace.maximum_primal_residual_ratio <= 1.0
    assert trace.maximum_dual_residual_ratio <= 1.0
    assert trace.base.maximum_constraint_residual <= 1.0e-8


def test_sparse_solver_matches_a_successful_legacy_prefix() -> None:
    from andes_rl_kundur.control.model_first_constrained_qp import (
        SparseConstrainedHorizonSolver,
        simulate_sparse_constrained_horizon_feedback,
    )

    plant, design, case = _sealed_failure_fixture()
    reference = simulate_constrained_horizon_feedback(
        plant,
        case.disturbance[:3],
        design=design,
        initial_soc=case.initial_soc,
    )
    candidate = simulate_sparse_constrained_horizon_feedback(
        plant,
        case.disturbance[:3],
        design=design,
        initial_soc=case.initial_soc,
    )
    solver = SparseConstrainedHorizonSolver(design)

    assert solver.action_optimum_is_unique
    assert solver.minimum_action_hessian_eigenvalue > 0.0
    np.testing.assert_allclose(
        candidate.base.coordinate_actions,
        reference.coordinate_actions,
        rtol=0.0,
        atol=1.0e-6,
    )
    np.testing.assert_allclose(
        candidate.base.node_actions,
        reference.node_actions,
        rtol=0.0,
        atol=1.0e-6,
    )
    np.testing.assert_allclose(
        candidate.base.outputs,
        reference.outputs,
        rtol=0.0,
        atol=1.0e-6,
    )
    np.testing.assert_allclose(
        candidate.base.soc,
        reference.soc,
        rtol=0.0,
        atol=1.0e-6,
    )
