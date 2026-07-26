from __future__ import annotations

import numpy as np
import pytest
import torch

from andes_rl_kundur.control.area_inertia_residual import (
    AREA_PATTERN,
    executed_md_actions_numpy,
    project_raw_to_q_numpy,
    project_raw_to_q_torch,
    q_from_signed_residual_observation,
    r278_area_inertia_contract,
)


def test_numpy_projection_is_one_dimensional_zero_sum() -> None:
    q, residual = project_raw_to_q_numpy(
        np.asarray([1.0, 0.5, -0.5, -1.0], dtype=np.float32),
    )
    assert float(q) == pytest.approx(0.1875)
    np.testing.assert_allclose(residual, float(q) * AREA_PATTERN)
    assert float(np.sum(residual)) == pytest.approx(0.0, abs=1e-12)
    assert residual[0] == residual[1]
    assert residual[2] == residual[3]


def test_projection_respects_scalar_slew_and_inactive_reset() -> None:
    raw = np.asarray([-1.0, -1.0, 1.0, 1.0], dtype=np.float32)
    q, residual = project_raw_to_q_numpy(raw, previous_q=0.25)
    assert float(q) == pytest.approx(0.0)
    np.testing.assert_allclose(residual, np.zeros(4))

    q_off, residual_off = project_raw_to_q_numpy(
        raw,
        previous_q=float(q),
        active=False,
    )
    assert float(q_off) == 0.0
    np.testing.assert_array_equal(residual_off, np.zeros(4))


def test_area_permutation_and_area_swap_equivariance() -> None:
    raw = np.asarray([0.8, 0.2, -0.4, -0.6], dtype=np.float32)
    q, residual = project_raw_to_q_numpy(raw)

    within_area = raw[[1, 0, 3, 2]]
    q_permuted, residual_permuted = project_raw_to_q_numpy(within_area)
    assert float(q_permuted) == pytest.approx(float(q))
    np.testing.assert_allclose(residual_permuted, residual)

    area_swapped = raw[[2, 3, 0, 1]]
    q_swapped, residual_swapped = project_raw_to_q_numpy(area_swapped)
    assert float(q_swapped) == pytest.approx(-float(q))
    np.testing.assert_allclose(residual_swapped, -residual)


def test_numpy_and_torch_projection_match_and_torch_has_gradient() -> None:
    raw_np = np.asarray(
        [[0.8, 0.2, -0.4, -0.6], [-0.2, 0.4, 0.7, -0.1]],
        dtype=np.float32,
    )
    prev_np = np.asarray([0.05, -0.10], dtype=np.float32)
    q_np, residual_np = project_raw_to_q_numpy(
        raw_np,
        previous_q=prev_np,
    )

    raw_t = torch.tensor(raw_np, requires_grad=True)
    q_t, residual_t = project_raw_to_q_torch(
        raw_t,
        previous_q=torch.tensor(prev_np),
    )
    np.testing.assert_allclose(q_t.detach().numpy(), q_np, atol=1e-7)
    np.testing.assert_allclose(
        residual_t.detach().numpy(),
        residual_np,
        atol=1e-7,
    )
    q_t.sum().backward()
    assert raw_t.grad is not None
    assert torch.count_nonzero(raw_t.grad).item() > 0


def test_executed_actions_match_r277_physical_safe_range_and_window() -> None:
    cfg = r278_area_inertia_contract()
    raw = np.asarray([1.0, 1.0, -1.0, -1.0], dtype=np.float32)
    q, residual, actions = executed_md_actions_numpy(
        raw,
        previous_q=0.0,
        step=0,
        contract=cfg,
    )
    assert q == pytest.approx(0.25)
    np.testing.assert_allclose(residual, [0.25, 0.25, -0.25, -0.25])
    np.testing.assert_allclose(actions[:, 0], [0.5, 0.5, 0.0, 0.0])
    np.testing.assert_array_equal(actions[:, 1], np.zeros(4))

    q_off, residual_off, actions_off = executed_md_actions_numpy(
        raw,
        previous_q=q,
        step=cfg.active_steps,
        contract=cfg,
    )
    assert q_off == 0.0
    np.testing.assert_array_equal(residual_off, np.zeros(4))
    np.testing.assert_array_equal(actions_off, np.zeros((4, 2)))


def test_previous_q_is_recovered_from_signed_observation() -> None:
    signed = torch.tensor(
        [[0.4, 0.4, -0.4, -0.4], [-1.0, -1.0, 1.0, 1.0]],
        dtype=torch.float32,
    )
    recovered = q_from_signed_residual_observation(signed)
    torch.testing.assert_close(recovered, torch.tensor([0.4, -1.0]))
