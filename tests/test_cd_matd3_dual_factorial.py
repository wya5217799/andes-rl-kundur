from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.agents.cd_matd3_dual_factorial import (
    balanced_dual_replay,
    projected_dual_step,
    replay_projected_dual,
)


def test_ceiling_persists_exactly_for_nonnegative_residual() -> None:
    assert projected_dual_step(10.0, 2.0, eta=0.05, ceiling=10.0) == 10.0
    assert projected_dual_step(10.0, 0.0, eta=0.05, ceiling=10.0) == 10.0
    assert projected_dual_step(10.0, -2.0, eta=0.05, ceiling=10.0) == 9.9


def test_replay_retains_pre_residual_post_alignment() -> None:
    result = replay_projected_dual(9.0, [2.0, -4.0], eta=0.5, ceiling=10.0)
    assert result["final_mu"] == 8.0
    assert result["trace"] == [
        {"index": 0, "mu_pre": 9.0, "residual_pre": 2.0, "mu_post": 10.0},
        {"index": 1, "mu_pre": 10.0, "residual_pre": -4.0, "mu_post": 8.0},
    ]


def test_balanced_aggregate_and_profile_have_equal_exposure_count() -> None:
    aggregate = balanced_dual_replay(
        10.0,
        {"a": 1.0, "b": 3.0},
        eta=0.1,
        ceiling=100.0,
        steps=4,
        per_profile=False,
    )
    profiles = balanced_dual_replay(
        10.0,
        {"a": 1.0, "b": 3.0},
        eta=0.1,
        ceiling=100.0,
        steps=4,
        per_profile=True,
    )
    assert aggregate["final"] == pytest.approx(10.8)
    assert profiles["final_by_profile"] == pytest.approx({"a": 10.4, "b": 11.2})
    assert np.mean(list(profiles["final_by_profile"].values())) == pytest.approx(aggregate["final"])


@pytest.mark.parametrize(
    "args",
    [
        (np.nan, 0.0, 0.1, 10.0),
        (0.0, 0.0, 0.0, 10.0),
        (11.0, 0.0, 0.1, 10.0),
    ],
)
def test_projected_dual_rejects_invalid_inputs(args: tuple[float, ...]) -> None:
    with pytest.raises(ValueError):
        projected_dual_step(args[0], args[1], eta=args[2], ceiling=args[3])
