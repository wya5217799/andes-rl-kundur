import importlib.util
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "run_r294_compact_controller_validation",
    ROOT / "scripts/run_r294_compact_controller_validation.py",
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_formal_scenarios_are_exact_development_complement():
    development = {row["name"] for row in MODULE.development.scenario_bank()}
    formal = {row["name"] for row in MODULE.scenario_bank()}
    assert len(development) == 4
    assert len(formal) == 12
    assert development.isdisjoint(formal)
    assert len(development | formal) == 16


def test_job_bank_is_matched_three_arm_matrix():
    jobs = MODULE.job_bank()
    assert len(jobs) == 36
    for scenario in MODULE.scenario_bank():
        names = {
            job["arm"]["name"]
            for job in jobs
            if job["scenario"]["name"] == scenario["name"]
        }
        assert names == {arm["name"] for arm in MODULE.arm_bank()}


def test_paired_ratio_bootstrap_is_deterministic_and_tracks_scale():
    baseline = np.arange(1.0, 13.0)
    candidate = 0.8 * baseline
    first = MODULE.paired_ratio_interval(candidate, baseline, seed=10, resamples=1000)
    second = MODULE.paired_ratio_interval(candidate, baseline, seed=10, resamples=1000)
    assert first == second
    assert first["point"] == pytest.approx(0.8)
    assert first["percentile_95_interval"] == pytest.approx([0.8, 0.8])


def test_candidate_gate_requires_both_common_and_differential_conditions():
    good = {
        "candidate_over_reference": {
            **{
                endpoint: {
                    "point": 1.0,
                    "percentile_95_interval": [0.99, 1.04],
                    "worst_individual_ratio": 1.08,
                }
                for endpoint in MODULE.COMMON_ENDPOINTS
            },
            **{
                endpoint: {
                    "point": 0.90,
                    "percentile_95_interval": [0.80, 0.99],
                    "worst_individual_ratio": 1.0,
                }
                for endpoint in MODULE.DIFFERENTIAL_ENDPOINTS
            },
        }
    }
    assert MODULE._candidate_gate(good)["passed"] is True
    good["candidate_over_reference"]["fast_inter_area_iae_hz_s"][
        "percentile_95_interval"
    ][1] = 1.01
    assert MODULE._candidate_gate(good)["passed"] is False
