from __future__ import annotations

import numpy as np

import scripts.run_r450_p2_delay_loop as runner


def test_scalar_delayed_response_matches_exact_law() -> None:
    loop = np.asarray([[0.5 + 0.2j]])
    disturbance = np.asarray([[1.0 + 0.0j]])
    z = np.exp(0.3j)
    actual = runner.delayed_response(loop, disturbance, z, 2)
    expected = 1.0 / (1.0 + loop * z**-2)
    np.testing.assert_allclose(actual, expected)


def test_classification_branches_and_endpoint_boundary() -> None:
    linear = {
        "predicted_r_d": {"0": 0.94, "1": 0.96, "2": 0.99},
        "min_return_difference_sigma": {"0": 0.5, "1": 0.4, "2": 0.3},
    }
    nonlinear = {
        "0": {"ratios": {"r_d": 0.94}},
        "1": {"ratios": {"r_d": 0.96}},
        "2": {"ratios": {"r_d": 0.99}},
    }
    result = runner._classify(linear, nonlinear)
    assert result["verdict"] == "PHASE-DELAY-CONSISTENT"
    assert result["endpoint_boundary"] == "BETWEEN-0-AND-1-SAMPLE-ENDPOINT-BOUNDARY"


def test_r450_uses_distinct_create_only_root() -> None:
    assert runner.ROUND == "R450"
    assert runner.OUT.name == "r450_p2_delay_loop"
