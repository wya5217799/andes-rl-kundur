#!/usr/bin/env python3
"""Lightweight self-tests for the R402 audit arithmetic and authority utilities."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np

from r402_authority_tools import (
    authority_metrics,
    build_componentwise_slew_matrix,
    common_gradient_ratio,
    finite_horizon_discrete_gramian,
    lifted_response_map,
    parameter_gradient_ratio,
    piecewise_md_decoder_slope,
    reduce_index1_dae,
    zoh_discretize,
)
from r402_recompute import write_outputs


def test_recompute() -> None:
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as tmp:
        result = write_outputs(root / "r402_audit_input.json", Path(tmp))
        counts = result["counts"]
        assert result["all_assertions_passed"] is True
        assert counts["total_files"] == 40
        assert counts["total_trajectories"] == 240
        assert counts["learning_trajectories"] == 216
        assert counts["action_component_samples_per_arm_seed"] == 5760
        generated = json.loads((Path(tmp) / "r402_audit_recomputed.json").read_text())
        assert generated["counts"]["total_trajectories"] == 240


def test_authority_tools() -> None:
    # Scalar DAE:
    # xdot = -2x + y + 3u; 0 = x + 2y + u
    # y = -(x+u)/2, hence A_r=-2.5 and B_u,r=2.5.
    reduced = reduce_index1_dae(
        f_x=[[-2.0]],
        f_y=[[1.0]],
        f_u=[[3.0]],
        g_x=[[1.0]],
        g_y=[[2.0]],
        g_u=[[1.0]],
    )
    assert np.allclose(reduced.A, [[-2.5]])
    assert np.allclose(reduced.B_u, [[2.5]])

    a_d, b_d = zoh_discretize(reduced.A, reduced.B_u, dt=0.2)
    lifted = lifted_response_map(a_d, b_d, C=[[1.0]], D=[[0.0]], horizon=3)
    assert lifted.shape == (3, 3)
    # With y[k] measured before u[k] affects x[k+1] and D=0, the final input has
    # no output within the same 3-step stack; numerical rank is therefore two.
    metrics = authority_metrics(lifted)
    assert metrics.numerical_rank == 2
    assert metrics.minimum_nonzero_singular_value > 0.0

    gramian = finite_horizon_discrete_gramian(a_d, b_d, horizon=3)
    assert gramian.shape == (1, 1)
    assert gramian[0, 0] > 0.0

    assert np.isclose(common_gradient_ratio(0.1, [2.0, 0.0], [1.0, 0.0]), 0.2)
    parameter_ratio = parameter_gradient_ratio(
        0.1,
        actor_action_jacobian=np.eye(2),
        grad_q_common=[2.0, 0.0],
        grad_q_differential=[1.0, 0.0],
    )
    assert np.isclose(parameter_ratio["common_to_differential_norm_ratio"], 0.2)
    assert np.isclose(parameter_ratio["cosine_between_contributions"], 1.0)

    slew = build_componentwise_slew_matrix(horizon=3, action_dim=2)
    assert slew.shape == (6, 6)
    slopes = piecewise_md_decoder_slope([-0.1, 0.2])
    assert np.allclose(np.diag(slopes), [200.0, 600.0])


def main() -> None:
    test_recompute()
    test_authority_tools()
    print("All R402 audit self-tests passed.")


if __name__ == "__main__":
    main()
