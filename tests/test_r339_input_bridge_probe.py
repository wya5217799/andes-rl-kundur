from __future__ import annotations

import numpy as np
from probes.r339_input_bridge_diagnosis import (
    analyse_derivative_family,
    classify_r339,
    trajectory_metrics,
)


def _family(scale: float = 1.0) -> dict[str, object]:
    f = np.asarray([[1.0, -2.0], [0.5, 3.0]])
    g = np.asarray([[4.0, -1.0]])
    return {
        "restored_exactly": True,
        "steps": [
            {
                "step_system_pu": step,
                "f_input": (factor * f).tolist(),
                "g_input": (factor * g).tolist(),
                "midpoint_ratios": [1e-8, 2e-8],
                "all_branch_snapshots_match": True,
            }
            for step, factor in zip(
                (1e-4, 1e-5, 1e-6),
                (1.0, 1.0, scale),
                strict=True,
            )
        ],
    }


def test_derivative_family_requires_scale_convergence_branch_and_restore() -> None:
    passed = analyse_derivative_family(
        _family(),
        relative_tolerance=1e-5,
        midpoint_tolerance=1e-6,
    )
    assert passed["pass"] is True
    assert passed["integrity_pass"] is True
    assert passed["convergence_pass"] is True
    assert passed["selected_step_system_pu"] == 1e-6

    drifted = analyse_derivative_family(
        _family(scale=1.01),
        relative_tolerance=1e-5,
        midpoint_tolerance=1e-6,
    )
    assert drifted["pass"] is False
    assert drifted["integrity_pass"] is True
    assert drifted["convergence_pass"] is False

    branch = _family()
    branch["steps"][1]["all_branch_snapshots_match"] = False
    assert (
        analyse_derivative_family(branch, relative_tolerance=1e-5, midpoint_tolerance=1e-6)[
            "integrity_pass"
        ]
        is False
    )


def test_trajectory_metrics_use_registered_vector_normalizations() -> None:
    truth = np.asarray([[1.0, 0.0], [0.0, 2.0]])
    prediction = np.asarray([[0.9, 0.0], [0.0, 2.2]])

    metrics = trajectory_metrics(prediction, truth)

    np.testing.assert_allclose(
        metrics["nrmse"],
        np.linalg.norm(prediction - truth) / np.linalg.norm(truth),
    )
    np.testing.assert_allclose(
        metrics["peak_vector_residual"],
        np.max(np.linalg.norm(prediction - truth, axis=1)) / np.max(np.linalg.norm(truth, axis=1)),
    )


def test_classification_stops_at_first_failed_gate() -> None:
    assert (
        classify_r339(
            validity_pass=False,
            descriptor_pass=False,
            linearization_pass=False,
            reduction_pass=False,
        )
        == "INVALID"
    )
    assert (
        classify_r339(
            validity_pass=True,
            descriptor_pass=False,
            linearization_pass=False,
            reduction_pass=False,
        )
        == "BLOCK-DESCRIPTOR"
    )
    assert (
        classify_r339(
            validity_pass=True, descriptor_pass=True, linearization_pass=False, reduction_pass=False
        )
        == "BLOCK-LINEARIZATION"
    )
    assert (
        classify_r339(
            validity_pass=True, descriptor_pass=True, linearization_pass=True, reduction_pass=False
        )
        == "QUALIFY-MECHANISM"
    )
    assert (
        classify_r339(
            validity_pass=True, descriptor_pass=True, linearization_pass=True, reduction_pass=True
        )
        == "ALLOW-CANDIDATE"
    )
