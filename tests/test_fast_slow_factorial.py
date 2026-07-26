import platform

import pytest

from andes_rl_kundur.evaluation.fast_slow_factorial import (
    ARMS,
    ENDPOINTS,
    classify_fast_slow_factorial,
    factorial_bootstrap,
    run_fast_only_scenario,
)

IS_WSL = platform.system() == "Linux" and "microsoft" in platform.release().lower()


def _endpoint_payload(values_by_arm):
    return {
        arm: {
            endpoint: list(values_by_arm[arm])
            for endpoint in ENDPOINTS
        }
        for arm in ARMS
    }


def test_factorial_bootstrap_reports_absolute_interaction_and_best_single():
    payload = _endpoint_payload(
        {
            "zero": [10.0, 12.0, 14.0, 16.0],
            "slow": [8.0, 10.0, 12.0, 14.0],
            "fast": [8.0, 10.0, 12.0, 14.0],
            "combined": [4.0, 6.0, 8.0, 10.0],
        }
    )

    result = factorial_bootstrap(
        payload,
        seed=123,
        n_resamples=2_000,
    )
    endpoint = result["endpoints"]["max_abs_rocof_hz_s"]

    assert endpoint["interaction"]["absolute_point"] == pytest.approx(-2.0)
    assert endpoint["interaction"]["percent_of_zero_point"] == pytest.approx(
        -100.0 * 2.0 / 13.0
    )
    assert endpoint["combined_minus_best_single"][
        "ratio_of_means_percent"
    ]["point"] == pytest.approx(100.0 * (7.0 / 11.0 - 1.0))
    assert endpoint["best_single_values"] == pytest.approx([8.0, 10.0, 12.0, 14.0])


def test_factorial_bootstrap_identifies_an_additive_combination():
    payload = _endpoint_payload(
        {
            "zero": [10.0, 12.0, 14.0, 16.0],
            "slow": [8.0, 10.0, 12.0, 14.0],
            "fast": [8.0, 10.0, 12.0, 14.0],
            "combined": [6.0, 8.0, 10.0, 12.0],
        }
    )

    result = factorial_bootstrap(
        payload,
        seed=123,
        n_resamples=2_000,
    )

    assert result["endpoints"]["max_abs_rocof_hz_s"]["interaction"][
        "absolute_point"
    ] == pytest.approx(0.0)


def _factorial_decisions(cleared):
    endpoints = {}
    for endpoint in ENDPOINTS:
        clear = endpoint in cleared
        endpoints[endpoint] = {
            "interaction": {
                "absolute_point": -1.0 if clear else 0.0,
                "absolute_percentile_95_interval": (
                    [-2.0, -0.1] if clear else [-0.5, 0.5]
                ),
                "percent_of_zero_point": -3.0 if clear else 0.0,
            },
            "combined_minus_best_single": {
                "ratio_of_means_percent": {
                    "point": -3.0 if clear else 0.0,
                    "percentile_95_interval": (
                        [-4.0, -0.1] if clear else [-1.0, 1.0]
                    ),
                }
            },
        }
    return {"endpoints": endpoints}


def test_factorial_gate_requires_fast_and_slow_nonadditive_value():
    result = classify_fast_slow_factorial(
        factorial=_factorial_decisions(
            {"max_abs_rocof_hz_s", "vsg_mean_iae_hz_s"}
        ),
        provenance_guard_pass=True,
        completion_guard_pass=True,
        action_storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert result["classification"] == "NONADDITIVE-POSITIVE"


def test_factorial_gate_is_partial_for_only_one_clearing_endpoint():
    result = classify_fast_slow_factorial(
        factorial=_factorial_decisions({"max_abs_rocof_hz_s"}),
        provenance_guard_pass=True,
        completion_guard_pass=True,
        action_storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert result["classification"] == "NONADDITIVE-PARTIAL"


def test_factorial_gate_is_additive_only_without_interaction():
    result = classify_fast_slow_factorial(
        factorial=_factorial_decisions(set()),
        provenance_guard_pass=True,
        completion_guard_pass=True,
        action_storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert result["classification"] == "ADDITIVE-ONLY"


def test_factorial_gate_is_invalid_on_reused_trace_provenance_failure():
    result = classify_fast_slow_factorial(
        factorial=_factorial_decisions(
            {"max_abs_rocof_hz_s", "vsg_mean_iae_hz_s"}
        ),
        provenance_guard_pass=False,
        completion_guard_pass=True,
        action_storage_guard_pass=True,
        tail_guard_pass=True,
    )

    assert result["classification"] == "INVALID"


@pytest.mark.skipif(not IS_WSL, reason="real ANDES integration runs only in WSL")
def test_fast_only_runner_has_exact_md_action_and_zero_storage_support():
    record = run_fast_only_scenario(
        "fast_only_smoke",
        {"PQ_Bus14": 1.0},
        seed=42,
        steps=20,
    )

    assert record["completed"] is True
    assert record["tds_failed"] is False
    assert record["traces"][0]["M_es"] == pytest.approx([350.0] * 4)
    assert record["traces"][15]["M_es"] == pytest.approx([200.0] * 4)
    for step in record["traces"]:
        assert step["bess_requested_power_system_pu"] == pytest.approx([0.0] * 4)
        assert step["bess_commanded_power_system_pu"] == pytest.approx([0.0] * 4)
        assert step["bess_actual_power_system_pu"] == pytest.approx([0.0] * 4)
        assert step["bess_soc"] == pytest.approx([0.5] * 4)
