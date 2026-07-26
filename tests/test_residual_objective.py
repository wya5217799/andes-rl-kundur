"""Tests for the prospectively fixed R269 residual objective."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.evaluation.residual_objective import (  # noqa: E402
    ResidualObjectiveConfig,
    frequency_mode_terms,
    residual_action_terms,
    residual_objective_terms,
    summarise_frequency_objective,
    summarise_residual_objective,
)


def test_uniform_shift_is_common_mode_only_at_existing_settling_band():
    terms = frequency_mode_terms([0.05, 0.05, 0.05, 0.05])

    assert terms["common_mode_hz"] == pytest.approx(0.05)
    assert terms["common"] == pytest.approx(1.0)
    assert terms["differential"] == pytest.approx(0.0)


def test_zero_mean_split_is_differential_mode_only():
    terms = frequency_mode_terms([0.05, -0.05, 0.05, -0.05])

    assert terms["common"] == pytest.approx(0.0)
    assert terms["differential_mse_hz2"] == pytest.approx(0.05**2)
    assert terms["differential"] == pytest.approx(1.0)


def test_zero_and_opposing_residuals_are_charged_per_agent_not_after_averaging():
    zero = residual_action_terms(np.zeros((4, 2)))
    opposing = residual_action_terms(
        [[1.0, 0.0], [-1.0, 0.0], [1.0, 0.0], [-1.0, 0.0]]
    )

    assert zero["residual_effort"] == pytest.approx(0.0)
    assert zero["residual_variation"] == pytest.approx(0.0)
    assert opposing["residual_effort"] == pytest.approx(0.5)
    assert opposing["residual_variation"] == pytest.approx(0.0)


def test_constant_residual_has_no_movement_but_sign_switch_does():
    current = np.full((4, 2), 0.5)
    same = residual_action_terms(current, previous_residual_actions=current)
    switched = residual_action_terms(
        -current,
        previous_residual_actions=current,
    )

    assert same["residual_variation"] == pytest.approx(0.0)
    assert switched["residual_variation_l1"] == pytest.approx(2.0)
    assert switched["residual_variation"] == pytest.approx(0.5)


def test_scalar_is_exact_sum_of_four_default_normalized_terms():
    terms = residual_objective_terms(
        [0.05, 0.05, 0.05, 0.05],
        np.full((4, 2), 0.5),
        previous_residual_actions=np.full((4, 2), -0.5),
    )

    expected = (
        terms["common"]
        + terms["differential"]
        + terms["residual_effort"]
        + terms["residual_variation"]
    )
    assert terms["total"] == pytest.approx(expected)


def test_frequency_summary_preserves_physical_endpoint_identities():
    delta_f = np.array(
        [
            [-0.10, -0.06],
            [-0.06, -0.02],
            [-0.04, -0.01],
            [-0.03, -0.01],
        ]
    )
    summary = summarise_frequency_objective(
        delta_f,
        sample_interval_s=0.2,
    )

    common = np.mean(delta_f, axis=1)
    sync = np.mean(np.square(delta_f - common[:, None]))
    assert summary["vsg_mean_iae_hz_s"] == pytest.approx(
        np.sum(np.abs(common)) * 0.2
    )
    assert summary["normalized_sync_loss_hz2"] == pytest.approx(sync)
    assert summary["common_normalized_sum"] * 0.05 * 0.2 == pytest.approx(
        summary["vsg_mean_iae_hz_s"]
    )
    assert summary["differential_normalized_mean"] * 0.05**2 == pytest.approx(
        summary["normalized_sync_loss_hz2"]
    )


def test_residual_summary_starts_variation_at_first_inter_step_difference():
    actions = np.array(
        [
            [[0.5, 0.0], [0.5, 0.0]],
            [[0.5, 0.0], [0.5, 0.0]],
            [[-0.5, 0.0], [-0.5, 0.0]],
        ]
    )
    summary = summarise_residual_objective(actions)

    assert summary["residual_total_variation"] == pytest.approx(1.0)
    assert summary["residual_variation_normalized_mean"] == pytest.approx(
        1.0 / 4.0 / 3.0
    )


@pytest.mark.parametrize(
    ("fn", "args", "match"),
    [
        (frequency_mode_terms, ([0.1, float("nan")],), "non-finite"),
        (residual_action_terms, ([0.0, 0.0],), "shape"),
        (
            residual_action_terms,
            ([[1.01, 0.0], [0.0, 0.0]],),
            r"\[-1, 1\]",
        ),
        (
            summarise_residual_objective,
            (np.zeros((2, 4, 3)),),
            "shape",
        ),
    ],
)
def test_objective_rejects_untrustworthy_input(fn, args, match):
    with pytest.raises(ValueError, match=match):
        fn(*args)


def test_config_rejects_non_positive_normalizer_and_negative_weight():
    with pytest.raises(ValueError, match="frequency_band_hz"):
        ResidualObjectiveConfig(frequency_band_hz=0.0)
    with pytest.raises(ValueError, match="common_weight"):
        ResidualObjectiveConfig(common_weight=-1.0)
