from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from andes_rl_kundur.evaluation.coupled_actuator_authority import (
    aggregate_authority,
    paired_authority_metrics,
    physical_coordinate_matrix,
)

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_r294_actuator_authority.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("r294_authority_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_physical_coordinate_matrix_is_orthonormal_and_named_rows_match() -> None:
    transform = physical_coordinate_matrix()
    np.testing.assert_allclose(transform @ transform.T, np.eye(4), atol=1e-12)
    np.testing.assert_allclose(transform[0], [0.5, 0.5, 0.5, 0.5])
    np.testing.assert_allclose(transform[1], [0.5, 0.5, -0.5, -0.5])


def test_paired_metrics_recover_target_and_zero_nonlinearity() -> None:
    baseline = np.zeros((4, 4))
    common = np.tile([0.5, 0.5, 0.5, 0.5], (4, 1))
    plus = baseline + common
    minus = baseline - common
    metrics = paired_authority_metrics(
        baseline,
        plus,
        minus,
        target_coordinate="common",
        dt_seconds=0.25,
        fast_steps=2,
    )
    assert metrics["target_l2_hz_sqrt_s"] == pytest.approx(1.0)
    assert metrics["cross_target_l2_ratio"] == pytest.approx(0.0, abs=1e-12)
    assert metrics["midpoint_nonlinearity_ratio"] == pytest.approx(0.0)


def test_aggregate_authority_applies_relative_and_linearity_gates() -> None:
    rows = []
    for actuator, gain, nonlinearity in (("M", 1.0, 0.1), ("D", 0.2, 0.1), ("P", 0.5, 0.6)):
        for scenario in range(2):
            rows.append(
                {
                    "coordinate": "common",
                    "actuator": actuator,
                    "scenario": scenario,
                    "metrics": {
                        "target_l2_hz_sqrt_s": gain,
                        "cross_target_l2_ratio": 0.2,
                        "midpoint_nonlinearity_ratio": nonlinearity,
                    },
                }
            )
    result = aggregate_authority(
        rows,
        relevance_ratio=0.25,
        linearity_median_max=0.25,
        linearity_worst_max=0.5,
    )
    common = result["coordinates"]["common"]
    assert common["dominant_budget_normalized_actuator"] == "M"
    assert common["budget_relevant_actuators"] == ["M", "P"]
    assert result["trajectory_model_decision"] == "TRAJECTORY-LINEARIZATION-NO-GO"


def test_runner_bank_and_physical_probe_mapping_are_frozen() -> None:
    runner = _load_runner()
    assert len(runner.scenario_bank()) == 16
    assert len(runner.arm_bank()) == 13
    assert len(runner.job_bank()) == 208

    common_plus = next(
        arm for arm in runner.arm_bank() if arm["name"] == "m__common__plus"
    )
    md, power = runner._commands(common_plus, 0)
    np.testing.assert_allclose(power, 0.0)
    np.testing.assert_allclose([md[index][0] for index in range(4)], 20.0 / 600.0)

    interarea_minus = next(
        arm for arm in runner.arm_bank() if arm["name"] == "p__interarea__minus"
    )
    md, power = runner._commands(interarea_minus, 0)
    np.testing.assert_allclose([md[index] for index in range(4)], 0.0)
    np.testing.assert_allclose(power, [-0.1, -0.1, 0.1, 0.1])

    md, power = runner._commands(interarea_minus, runner.ACTIVE_STEPS)
    np.testing.assert_allclose([md[index] for index in range(4)], 0.0)
    np.testing.assert_allclose(power, 0.0)
