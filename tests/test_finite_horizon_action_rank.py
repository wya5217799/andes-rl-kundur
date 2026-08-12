from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.evaluation.finite_horizon_action_rank import (
    finite_horizon_action_rank,
)


def test_rank_profile_separates_common_and_differential_authority() -> None:
    plus = np.zeros((4, 2, 4), dtype=float)
    minus = np.zeros_like(plus)
    amplitudes = np.asarray([0.5, 1.0, 2.0, 4.0])
    for action in range(4):
        plus[action, 0, action] = amplitudes[action]
        minus[action, 0, action] = -amplitudes[action]

    result = finite_horizon_action_rank(
        plus,
        minus,
        amplitudes=amplitudes,
        output_transform=np.eye(4),
        relative_thresholds=(0.1, 0.01),
    )

    assert result["action_count"] == 4
    assert result["sample_count"] == 2
    assert result["all_outputs"]["singular_values"] == pytest.approx(
        [1.0, 1.0, 1.0, 1.0]
    )
    assert result["all_outputs"]["stable_rank"] == pytest.approx(4.0)
    assert result["all_outputs"]["relative_effective_rank"] == {
        "0.01": 4,
        "0.1": 4,
    }
    assert result["common_output"]["stable_rank"] == pytest.approx(1.0)
    assert result["common_output"]["relative_effective_rank"] == {
        "0.01": 1,
        "0.1": 1,
    }
    assert result["differential_outputs"]["stable_rank"] == pytest.approx(3.0)
    assert result["differential_outputs"]["relative_effective_rank"] == {
        "0.01": 3,
        "0.1": 3,
    }


def test_rank_profile_rejects_nonpositive_action_amplitudes() -> None:
    traces = np.zeros((2, 3, 4), dtype=float)

    with pytest.raises(ValueError, match="amplitudes must be finite and positive"):
        finite_horizon_action_rank(
            traces,
            traces,
            amplitudes=[0.1, 0.0],
            output_transform=np.eye(4),
        )
