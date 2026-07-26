"""Tests for the frozen R270 scheduled basis controller."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.attainable_oracle import (  # noqa: E402
    CANDIDATE_SPECS,
    ScheduledBasisResidualController,
    candidate_contract,
)


def _obs(value: float = 0.02) -> dict[int, np.ndarray]:
    return {
        i: np.asarray([0.0, value, 0.0, 0.0, 0.0, 0.0, 0.0])
        for i in range(4)
    }


def test_candidate_library_exactly_spans_frozen_names_and_directions():
    assert [spec.name for spec in CANDIDATE_SPECS] == [
        "common_M_pos",
        "common_M_neg",
        "common_D_pos",
        "common_D_neg",
        "area_M_pos",
        "area_M_neg",
        "area_D_pos",
        "area_D_neg",
    ]
    assert CANDIDATE_SPECS[4].residual_matrix(0.25)[:, 0].tolist() == [
        0.25,
        0.25,
        -0.25,
        -0.25,
    ]


def test_scheduled_residual_is_active_for_exactly_first_15_steps():
    controller = ScheduledBasisResidualController(CANDIDATE_SPECS[0])

    at_zero = controller(0, _obs(0.0), 4)
    at_fourteen = controller(14, _obs(0.0), 4)
    at_fifteen = controller(15, _obs(0.0), 4)

    np.testing.assert_allclose(at_zero[0], [0.25, 0.0])
    np.testing.assert_allclose(at_fourteen[3], [0.25, 0.0])
    np.testing.assert_allclose(at_fifteen[0], [0.0, 0.0])


def test_scheduled_damping_composes_with_and_clips_droop():
    controller = ScheduledBasisResidualController(CANDIDATE_SPECS[2])

    actions = controller(0, _obs(0.10), 4)

    for action in actions.values():
        np.testing.assert_allclose(action, [0.0, 1.0])
    assert controller.telemetry()["executed_clipped_component_fraction"] > 0.0


def test_area_damping_signs_preserve_agent_area_partition():
    controller = ScheduledBasisResidualController(CANDIDATE_SPECS[6])

    actions = controller(0, _obs(0.0), 4)

    assert [float(actions[i][1]) for i in range(4)] == [
        0.25,
        0.25,
        -0.25,
        -0.25,
    ]


def test_candidate_contract_is_machine_readable_and_complete():
    contract = candidate_contract(amplitude=0.25, active_steps=15, k_droop=10)

    assert contract["amplitude"] == 0.25
    assert contract["active_steps"] == 15
    assert contract["area_of_agent"] == [1, 1, 2, 2]
    assert len(contract["candidates"]) == 8


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amplitude": -0.1, "active_steps": 15, "k_droop": 10},
        {"amplitude": 1.1, "active_steps": 15, "k_droop": 10},
        {"amplitude": 0.25, "active_steps": 0, "k_droop": 10},
        {"amplitude": 0.25, "active_steps": 15, "k_droop": -1},
    ],
)
def test_contract_rejects_invalid_values(kwargs):
    with pytest.raises(ValueError):
        candidate_contract(**kwargs)


def test_controller_rejects_non_four_agent_use():
    controller = ScheduledBasisResidualController(CANDIDATE_SPECS[0])

    with pytest.raises(ValueError, match="requires 4 agents"):
        controller(0, _obs(), 3)
