"""Tests for the R271 offline actuator-authority calculations."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from audit_actuator_authority import (  # noqa: E402
    _aggregate_window_effects,
    percent_effect,
    window_metrics,
)


def _record(scale: float = 1.0) -> dict:
    traces = []
    for index in range(150):
        common = scale * (0.05 - 0.0002 * index)
        differential = np.asarray([0.01, -0.01, 0.01, -0.01])
        traces.append(
            {
                "t": 0.2 * (index + 1),
                "delta_f_physical_hz": (common + differential).tolist(),
                "delta_P_es": [0.5, 0.5, 0.5, 0.5],
            }
        )
    return {
        "completed": True,
        "tds_failed": False,
        "n_steps": 150,
        "traces": traces,
    }


def test_window_metrics_separate_common_differential_and_power():
    metrics = window_metrics(_record(), start=0, stop=15)

    assert metrics["n_steps"] == 15
    assert metrics["common_iae_hz_s"] > 0.0
    assert metrics["differential_mse_hz2"] == pytest.approx(0.01**2)
    assert metrics["vsg_power_mean_pu"] == pytest.approx(0.5)


def test_negative_window_selects_exact_terminal_length():
    metrics = window_metrics(_record(), start=-25, stop=150)

    assert metrics["n_steps"] == 25
    assert metrics["terminal_common_abs_hz"] == pytest.approx(
        abs(0.05 - 0.0002 * 149)
    )


def test_percent_effect_is_lower_is_better_and_handles_zero_reference():
    assert percent_effect(0.8, 1.0) == pytest.approx(-20.0)
    assert percent_effect(1.2, 1.0) == pytest.approx(20.0)
    assert percent_effect(0.0, 0.0) is None


def test_aggregate_window_effects_pairs_records_and_preserves_direction():
    baseline = [_record(1.0), _record(1.0)]
    candidate = [_record(0.8), _record(0.8)]

    result = _aggregate_window_effects(
        candidate,
        baseline,
        start=0,
        stop=15,
    )

    assert result["candidate_minus_baseline_percent"][
        "common_abs_mean_hz"
    ] == pytest.approx(-20.0)
    assert result["candidate_minus_baseline_percent"][
        "differential_mse_hz2"
    ] == pytest.approx(0.0)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record.update(completed=False),
        lambda record: record["traces"].pop(),
        lambda record: record["traces"][0].update(
            delta_f_physical_hz=[float("nan")] * 4
        ),
    ],
)
def test_window_metrics_reject_untrustworthy_trace(mutation):
    record = _record()
    mutation(record)

    with pytest.raises(ValueError):
        window_metrics(record, start=0, stop=15)


def test_aggregate_rejects_unpaired_inputs():
    with pytest.raises(ValueError, match="paired"):
        _aggregate_window_effects(
            [_record()],
            [_record(), _record()],
            start=0,
            stop=15,
        )
