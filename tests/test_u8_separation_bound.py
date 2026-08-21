from __future__ import annotations

import numpy as np

from andes_rl_kundur.evaluation import u8_separation_bound as u8


def test_registered_io_projectors_are_orthogonal_and_complete() -> None:
    checks = u8.projector_checks(u8.projectors())
    assert checks["passed"] is True


def test_toeplitz_matches_independent_direct_impulses() -> None:
    rng = np.random.default_rng(42)
    n = 3
    model = {
        "A_post": 0.2 * np.eye(n),
        "B_post": rng.normal(size=(n, 7)),
        "C_post": rng.normal(size=(4, n)),
        "D_post": rng.normal(size=(4, 7)),
    }
    formula = u8.toeplitz_lift(model)
    direct = u8.direct_impulse_lift(model)
    assert formula.shape == (90, 30)
    assert np.max(np.abs(formula - direct)) <= 1.0e-14


def test_scaled_values_preserve_mean_and_scale_deviations() -> None:
    values = np.asarray([1.0, 2.0, 4.0, 5.0])
    scaled = u8.scaled_values(values, 0.25)
    assert np.isclose(np.mean(scaled), np.mean(values))
    assert np.allclose(scaled - np.mean(scaled), 0.25 * (values - np.mean(values)))
