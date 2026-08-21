"""Slice-5 tests: folded linear-model energy and input-column folding.

The folded-LTI simulator is validated against the independent closed-form
reduced swing simulation (probes.homogenization_linearization.linear_cross_energy)
on the same 4-unit ring network: both code paths must agree.
"""

from __future__ import annotations

import numpy as np
import pytest

from probes.homogenization_linearization import (  # noqa: E402
    REGISTERED_DIFFERENTIAL_TRANSFORM,
    linear_cross_energy,
)
from andes_rl_kundur.evaluation.r405_linearization import (  # noqa: E402
    fold_input_columns,
    folded_linear_probe_energy,
    reduced_swing_matrices,
)

RING_L = np.array([
    [2.0, -1.0, 0.0, -1.0],
    [-1.0, 2.0, -1.0, 0.0],
    [0.0, -1.0, 2.0, -1.0],
    [-1.0, 0.0, -1.0, 2.0],
])

DT = 0.2
OMEGA_N = 2.0 * np.pi * 60.0


def _probe_bank(magnitude: float) -> tuple[np.ndarray, np.ndarray]:
    common = np.full((30, 4), magnitude)
    differential = np.tile(
        np.array([magnitude, -magnitude, 0.5 * magnitude, -0.5 * magnitude]),
        (30, 1),
    )
    return common, differential


def _folded_case(m, d):
    a, b = reduced_swing_matrices(RING_L, [m] * 4, [d] * 4, OMEGA_N)
    c = np.hstack([np.zeros((4, 4)), np.eye(4)])
    return a, b, c


def test_folded_energy_matches_reduced_simulator_homogeneous():
    common, differential = _probe_bank(0.01)
    m, d = 200.0, 90.0
    a, b, c = _folded_case(m, d)
    folded = folded_linear_probe_energy(
        a, b, c, [common, -common], [differential, -differential],
        dt=DT, transform=REGISTERED_DIFFERENTIAL_TRANSFORM,
    )
    reduced = linear_cross_energy(
        RING_L, [m] * 4, [d] * 4, [common, -common], [differential, -differential],
    )
    assert folded["E_d_from_c"] == pytest.approx(reduced["E_d_from_c"], rel=1e-9)
    assert folded["E_c_from_d"] == pytest.approx(reduced["E_c_from_d"], rel=1e-9)
    assert folded["E_cross"] == pytest.approx(0.0, abs=1e-9)


def test_folded_energy_matches_reduced_simulator_heterogeneous():
    common, differential = _probe_bank(0.01)
    m, d = 200.0, 90.0
    a, b, c = _folded_case(m, d)
    # Heterogeneous M but same reduced matrices is physically wrong; instead
    # build the heterogeneous case with matching reduced matrices.
    a_het, b_het = reduced_swing_matrices(RING_L, [100.0, 300.0, 150.0, 250.0], [d] * 4, OMEGA_N)
    folded = folded_linear_probe_energy(
        a_het, b_het, c, [common, -common], [differential, -differential],
        dt=DT, transform=REGISTERED_DIFFERENTIAL_TRANSFORM,
    )
    reduced = linear_cross_energy(
        RING_L, [100.0, 300.0, 150.0, 250.0], [d] * 4,
        [common, -common], [differential, -differential],
    )
    assert folded["E_d_from_c"] == pytest.approx(reduced["E_d_from_c"], rel=1e-9)
    assert folded["E_cross"] > 0.0


def test_fold_input_columns_hand_case():
    # f_u = [[1,2],[3,4]], g_u = [[5,6],[7,8]], f_y = [[0.5,0],[0,0.5]],
    # g_y = [[2,0],[0,2]] -> B = f_u - f_y g_y^-1 g_u
    #   = f_u - 0.25 g_u = [[-0.25, 0.5],[1.25, 2.0]].
    f_u = np.array([[1.0, 2.0], [3.0, 4.0]])
    g_u = np.array([[5.0, 6.0], [7.0, 8.0]])
    f_y = np.diag([0.5, 0.5])
    g_y = np.diag([2.0, 2.0])
    b = fold_input_columns(f_u, g_u, f_y, g_y)
    expected = f_u - 0.25 * g_u
    assert np.allclose(b, expected, atol=1e-12)


def test_fold_input_columns_accepts_flat_residual_vectors():
    # The R405 execute-path bug: ANDES residual vectors arrive 1-D and must
    # be treated as a single input column.
    b = fold_input_columns(
        np.array([1.0, 2.0]),
        np.array([5.0, 6.0]),
        np.diag([0.5, 0.5]),
        np.diag([2.0, 2.0]),
    )
    # B = f_u - f_y g_y^-1 g_u = [1,2] - diag(0.25) @ [5,6] = [-0.25, 0.5].
    assert b.shape == (2, 1)
    assert np.allclose(b, np.array([-0.25, 0.5]).reshape(-1, 1), atol=1e-12)


def test_fold_input_columns_allows_mismatched_row_counts():
    # The real descriptor has n_state f-rows and n_alg g-rows; only the
    # column count must match.  f_y g_y^-1 g_u = [[1.25],[1.5],[0]].
    b = fold_input_columns(
        np.array([1.0, 2.0, 3.0]).reshape(-1, 1),
        np.array([5.0, 6.0]).reshape(-1, 1),
        np.array([[0.5, 0.0], [0.0, 0.5], [0.0, 0.0]]),
        np.diag([2.0, 2.0]),
    )
    assert b.shape == (3, 1)
    assert np.allclose(b, np.array([-0.25, 0.5, 3.0]).reshape(-1, 1), atol=1e-12)


def test_fold_input_columns_rejects_singular_g_y():
    with pytest.raises(ValueError):
        fold_input_columns(np.eye(2), np.eye(2), np.eye(2), np.zeros((2, 2)))