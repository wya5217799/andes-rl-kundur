from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation import u7_local_taylor as u7


def test_additive_lift_matches_direct_recursion() -> None:
    a = np.asarray([[0.8]])
    b = np.asarray([[1.0, -1.0, 0.0, 0.0]])
    c = np.asarray([[1.0], [-1.0], [0.0], [0.0]])
    d = np.zeros((4, 4))
    lift = u7.additive_lift(a, b, c, d)
    assert lift.shape == (90, 90)
    assert np.all(np.isfinite(lift))


def test_bilinear_lift_has_declared_complete_shape() -> None:
    n, r, p = 2, 3, 4
    a = 0.5 * np.eye(n)
    c = np.ones((p, n))
    n_tensor = np.ones((8, n, n))
    e_tensor = np.ones((8, n, r))
    r_tensor = np.ones((8, p, n))
    s_tensor = np.ones((8, p, r))
    lift = u7.bilinear_lift(a, c, n_tensor, e_tensor, r_tensor, s_tensor)
    assert lift.shape == (u7.HORIZON * p, u7.HORIZON * 8 * (n + r))
    assert np.all(np.isfinite(lift))


def test_convergence_accepts_exact_and_rejects_large_drift() -> None:
    levels = np.zeros((2, 3, 2, 2))
    levels[0] = 1.0
    levels[1, 1] = 1.0
    levels[1, 2] = 2.0
    rows = u7.convergence(levels)
    assert rows[0]["passed"] is True
    assert rows[1]["passed"] is False
