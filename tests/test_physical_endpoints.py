"""Tests for transparent 60-Hz physical endpoint reporting."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.physical_endpoints import (  # noqa: E402
    summarise_physical_trace,
)


def _record() -> dict:
    delta_f = [
        [-0.10, -0.06],
        [-0.06, -0.02],
        [-0.04, -0.01],
        [-0.03, -0.01],
    ]
    actions = [
        [[0.0, 0.0], [0.0, 0.0]],
        [[0.5, 1.0], [0.0, -1.0]],
        [[0.5, 0.5], [0.0, -0.5]],
        [[0.0, 0.0], [0.0, 0.0]],
    ]
    return {
        "completed": True,
        "tds_failed": False,
        "n_steps": 4,
        "frequency_reporting_basis": "legacy_control_hz",
        "andes_nominal_frequency_hz": 60.0,
        "traces": [
            {
                "t": 0.2 * (i + 1),
                "delta_f_physical_hz": values,
                "action_norm": actions[i],
            }
            for i, values in enumerate(delta_f)
        ],
    }


def test_physical_endpoints_use_physical_frequency_and_explicit_vsg_mean():
    result = summarise_physical_trace(_record(), settling_band_hz=0.05)

    assert result["andes_nominal_frequency_hz"] == 60.0
    assert result["sample_interval_s"] == pytest.approx(0.2)
    assert result["worst_bus_peak_abs_hz"] == pytest.approx(0.10)
    assert result["vsg_mean_peak_abs_hz"] == pytest.approx(0.08)
    assert result["vsg_mean_iae_hz_s"] == pytest.approx(0.033)
    assert result["terminal_worst_bus_abs_hz"] == pytest.approx(0.03)
    assert result["settling_time_s"] == pytest.approx(0.6)
    assert result["max_abs_rocof_hz_s"] == pytest.approx(0.20)
    expected_sync = sum(
        sum((value - sum(row) / len(row)) ** 2 for value in row) / len(row)
        for row in [
            [-0.10, -0.06],
            [-0.06, -0.02],
            [-0.04, -0.01],
            [-0.03, -0.01],
        ]
    ) / 4
    assert result["normalized_sync_loss_hz2"] == pytest.approx(expected_sync)
    assert result["action_saturation_fraction"] == pytest.approx(2 / 16)


def test_physical_endpoints_report_missing_action_telemetry_without_guessing():
    record = _record()
    for step in record["traces"]:
        step.pop("action_norm")

    result = summarise_physical_trace(record)

    assert result["action_l1_agent_s"] is None
    assert result["action_total_variation"] is None
    assert result["action_saturation_fraction"] is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record.update(completed=False),
        lambda record: record.update(frequency_reporting_basis="physical"),
        lambda record: record["traces"][0].update(delta_f_physical_hz=[float("nan")]),
    ],
)
def test_physical_endpoints_reject_untrustworthy_records(mutation):
    record = _record()
    mutation(record)

    with pytest.raises(ValueError):
        summarise_physical_trace(record)
