"""Slice-7 tests: E-weighted fold for the zero-Tf descriptor."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


from andes_rl_kundur.evaluation.r405_linearization import fold_with_e


def test_fold_with_e_hand_case():
    # E = diag(2, 4); f_x = diag(2, 4); f_alg = [[1,0],[0,2]];
    # g_x = [[0.5,0],[0,0.25]]; g_alg = diag(2, 2)
    # A = E^-1 (f_x - f_alg g_alg^-1 g_x)
    #   = diag(1/2, 1/4) (diag(2,4) - diag(1*0.5*0.5, 2*0.5*0.25))
    #   = diag(1/2, 1/4) diag(1.75, 3.75) = diag(0.875, 0.9375).
    out = fold_with_e(
        np.array([2.0, 4.0]),
        np.diag([2.0, 4.0]),
        np.array([[1.0, 0.0], [0.0, 2.0]]),
        np.array([[0.5, 0.0], [0.0, 0.25]]),
        np.diag([2.0, 2.0]),
    )
    assert out["ok"] is True
    assert np.allclose(out["A"], np.diag([0.875, 0.9375]), atol=1e-12)


def test_fold_with_e_accepts_diagonal_matrix_e():
    # The bridge stores e_d as a diagonal matrix; both forms must agree.
    vector_out = fold_with_e(
        np.array([2.0, 4.0]),
        np.diag([2.0, 4.0]),
        np.array([[1.0, 0.0], [0.0, 2.0]]),
        np.array([[0.5, 0.0], [0.0, 0.25]]),
        np.diag([2.0, 2.0]),
    )
    matrix_out = fold_with_e(
        np.diag([2.0, 4.0]),
        np.diag([2.0, 4.0]),
        np.array([[1.0, 0.0], [0.0, 2.0]]),
        np.array([[0.5, 0.0], [0.0, 0.25]]),
        np.diag([2.0, 2.0]),
    )
    assert np.allclose(matrix_out["A"], vector_out["A"], atol=1e-12)


def test_fold_with_e_rejects_nonpositive_e():
    with pytest.raises(ValueError):
        fold_with_e(
            np.array([0.0, 4.0]),
            np.eye(2),
            np.eye(2),
            np.eye(2),
            np.eye(2),
        )


def test_fold_with_e_singular_algebraic_reports_failure():
    out = fold_with_e(
        np.array([2.0, 4.0]),
        np.eye(2),
        np.eye(2),
        np.eye(2),
        np.zeros((2, 2)),
    )
    assert out["ok"] is False
    assert out["A"] is None