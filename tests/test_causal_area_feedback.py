"""Focused R279 tests for the causal area-feedback comparator."""

from __future__ import annotations

import numpy as np
import pytest

from andes_rl_kundur.control.causal_area_feedback import (
    CausalAreaFeedbackContract,
    CausalAreaFeedbackController,
    area_feedback_features,
    r279_causal_contracts,
)


def _obs() -> np.ndarray:
    return np.zeros((4, 7), dtype=np.float32)


def test_gain_family_is_frozen_and_nonzero() -> None:
    contracts = r279_causal_contracts()
    assert len(contracts) == 9
    assert len({(row.k_frequency, row.k_rocof) for row in contracts}) == 9
    assert all(row.k_frequency > 0.0 or row.k_rocof > 0.0 for row in contracts)


def test_area_features_reconstruct_physical_units() -> None:
    obs = _obs()
    obs[:2, 0] = 0.2
    obs[2:, 0] = -0.1
    obs[:2, 3] = 0.4
    obs[2:, 3] = 0.1
    delta_f_ab, delta_rocof_ab = area_feedback_features(obs)
    assert delta_f_ab == pytest.approx(0.03)
    assert delta_rocof_ab == pytest.approx(0.15)


def test_negative_feedback_and_area_swap_equivariance() -> None:
    controller = CausalAreaFeedbackController(
        CausalAreaFeedbackContract(k_frequency=0.5, k_rocof=0.25)
    )
    obs = _obs()
    obs[:2, 0] = 0.5
    obs[2:, 0] = -0.5
    obs[:2, 3] = 0.25
    obs[2:, 3] = -0.25
    raw = controller.select_raw_actions(obs)
    assert raw.shape == (4,)
    assert np.all(raw[:2] < 0.0)
    assert np.all(raw[2:] > 0.0)
    assert np.sum(raw) == pytest.approx(0.0, abs=1e-7)

    swapped = obs[[2, 3, 0, 1]]
    raw_swapped = controller.select_raw_actions(swapped)
    assert np.allclose(raw_swapped, -raw, rtol=0.0, atol=1e-7)


def test_within_area_permutation_invariance_and_bounds() -> None:
    controller = CausalAreaFeedbackController(
        CausalAreaFeedbackContract(k_frequency=1.0, k_rocof=1.0)
    )
    obs = _obs()
    obs[:, 0] = np.asarray([5.0, 1.0, -4.0, -2.0], dtype=np.float32)
    obs[:, 3] = np.asarray([5.0, 0.0, -5.0, -1.0], dtype=np.float32)
    raw = controller.select_raw_actions(obs)
    permuted = obs[[1, 0, 3, 2]]
    assert np.allclose(
        raw,
        controller.select_raw_actions(permuted),
        rtol=0.0,
        atol=1e-7,
    )
    assert np.max(np.abs(raw)) <= 1.0


def test_zero_observation_emits_zero_votes() -> None:
    controller = CausalAreaFeedbackController(
        CausalAreaFeedbackContract(k_frequency=0.5, k_rocof=0.5)
    )
    assert np.array_equal(
        controller.select_raw_actions(_obs()),
        np.zeros(4, dtype=np.float32),
    )
