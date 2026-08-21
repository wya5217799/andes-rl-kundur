"""Slice-1 tests for the R405 homogenization linear-model probe.

These tests lock the pure offline mathematics of the R405 plan before any
ANDES run: the asymmetric piecewise M/D codec, the per-profile homogenization
targets, the leading cross-channel moments, the common/differential
commutator checks, and the descriptor fold.  Every expected value comes from
an independent source (exact fractions or hand-derived matrix algebra), never
from re-running the implementation formula.
"""

from __future__ import annotations

import math
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest


from probes.homogenization_linearization import (  # noqa: E402
    HomogenizationTargets,
    commutator_checks,
    common_differential_projectors,
    delta_from_normalized,
    fold_descriptor,
    homogenization_targets,
    leading_cross_moments,
    normalized_target_from_delta,
)

# ---------------------------------------------------------------------------
# Cycle 1 - asymmetric piecewise codec (seal decoder constants, V4 env path)
# ---------------------------------------------------------------------------


def test_delta_from_normalized_piecewise():
    assert delta_from_normalized(0.0) == 0.0
    assert delta_from_normalized(0.5) == 300.0
    assert delta_from_normalized(1.0) == 600.0
    assert delta_from_normalized(-0.5) == -100.0
    assert delta_from_normalized(-1.0) == -200.0


def test_normalized_target_from_delta_piecewise():
    assert normalized_target_from_delta(0.0) == 0.0
    assert normalized_target_from_delta(300.0) == 0.5
    assert normalized_target_from_delta(600.0) == 1.0
    assert normalized_target_from_delta(-100.0) == -0.5
    assert normalized_target_from_delta(-200.0) == -1.0


def test_codec_roundtrip_on_random_deltas():
    rng = np.random.default_rng(405)
    for _ in range(200):
        delta = rng.uniform(-200.0, 600.0)
        u = normalized_target_from_delta(delta)
        assert -1.0 <= u <= 1.0
        assert delta_from_normalized(u) == pytest.approx(delta, abs=1e-9)


# ---------------------------------------------------------------------------
# Cycle 1 - homogenization targets on the real canary_dev_a profile
# ---------------------------------------------------------------------------


def test_homogenization_targets_dev_a_intervals_and_reachability():
    m0 = [150.0, 250.0, 170.0, 230.0]
    d0 = [60.0, 140.0, 80.0, 120.0]
    t = homogenization_targets(m0, d0)
    assert isinstance(t, HomogenizationTargets)
    assert t.reachable is True
    assert t.m_interval == pytest.approx((50.0, 750.0), rel=1e-12)
    assert t.d_interval == pytest.approx((10.0, 660.0), rel=1e-12)


def test_homogenization_targets_dev_a_fraction_exact():
    m0 = [150.0, 250.0, 170.0, 230.0]
    d0 = [60.0, 140.0, 80.0, 120.0]
    t = homogenization_targets(m0, d0)
    # Exact expected values via rational arithmetic (independent source).
    m_star_frac = Fraction(4, sum(Fraction(1, int(m)) for m in m0))
    d_over_m2_mean = (
        sum(Fraction(int(d), int(m) ** 2) for m, d in zip(m0, d0)) / 4
    )
    d_star_frac = m_star_frac**2 * d_over_m2_mean
    assert t.m_star == pytest.approx(float(m_star_frac), rel=1e-12)
    assert t.d_star == pytest.approx(float(d_star_frac), rel=1e-12)
    # Normalized targets follow the piecewise codec exactly.
    for i, (m, d) in enumerate(zip(m0, d0)):
        dm = m_star_frac - int(m)
        dd = d_star_frac - int(d)
        expected_u_m = float(dm / 600 if dm >= 0 else dm / 200)
        expected_u_d = float(dd / 600 if dd >= 0 else dd / 200)
        assert t.normalized_targets[i, 0] == pytest.approx(expected_u_m, rel=1e-12)
        assert t.normalized_targets[i, 1] == pytest.approx(expected_u_d, rel=1e-12)


def test_homogenization_targets_infeasible_spread():
    t = homogenization_targets([100.0, 1000.0], [10.0, 10.0])
    assert t.reachable is False
    assert t.m_star is None
    assert t.d_star is None
    assert t.normalized_targets is None


def test_homogenization_targets_respects_physical_floor():
    # M0=100 with the -200 lower box would go negative; the M>=20 floor binds.
    t = homogenization_targets([100.0, 100.0], [10.0, 10.0])
    assert t.m_interval[0] == 20.0
    assert t.d_interval[0] == 10.0


# ---------------------------------------------------------------------------
# Cycle 2 - leading cross moments (hand-derived two-unit case)
# ---------------------------------------------------------------------------


def test_common_differential_projectors_shape():
    q, pc, pd = common_differential_projectors(4)
    assert q.shape == (4, 1)
    assert pc.shape == (4, 4)
    assert pd.shape == (4, 4)
    assert np.allclose(pc, np.full((4, 4), 0.25), atol=1e-12)
    assert np.allclose(pc @ pd, np.zeros((4, 4)), atol=1e-12)


def test_leading_cross_moments_two_unit_hand_values():
    # M=[1,3], D=[1,1]: hand-derived from the 1/sqrt(n) basis.
    r = leading_cross_moments([1.0, 3.0], [1.0, 1.0])
    assert r["variance_inverse_M"] == pytest.approx(Fraction(1, 9), rel=1e-12)
    assert r["variance_D_over_M2"] == pytest.approx(Fraction(16, 81), rel=1e-12)
    assert r["projected_inverse_M_norm"] == pytest.approx(Fraction(1, 3), rel=1e-12)


def test_leading_cross_moments_homogeneous_is_zero():
    r = leading_cross_moments([2.0, 2.0, 2.0, 2.0], [5.0, 5.0, 5.0, 5.0])
    assert r["variance_inverse_M"] == 0.0
    assert r["variance_D_over_M2"] == 0.0
    assert r["projected_inverse_M_norm"] == 0.0


# ---------------------------------------------------------------------------
# Cycle 2 - commutator checks on a balanced four-node ring Laplacian
# ---------------------------------------------------------------------------

RING_L = np.array([
    [2.0, -1.0, 0.0, -1.0],
    [-1.0, 2.0, -1.0, 0.0],
    [0.0, -1.0, 2.0, -1.0],
    [-1.0, 0.0, -1.0, 2.0],
])


def test_commutator_checks_balanced_ring_l():
    r = commutator_checks(RING_L, [1.0, 2.0, 3.0, 4.0], [5.0, 5.0, 5.0, 5.0])
    assert r["L_right_balance"] == pytest.approx(0.0, abs=1e-12)
    assert r["L_left_balance"] == pytest.approx(0.0, abs=1e-12)
    assert r["commutator_L"] == pytest.approx(0.0, abs=1e-12)
    assert r["commutator_D"] == pytest.approx(0.0, abs=1e-12)


def test_commutator_checks_heterogeneous_m_hand_value():
    # [Pc, diag(1,2,3,4)] Frobenius = sqrt(2.5); rel vs ||M||_F = sqrt(30).
    r = commutator_checks(RING_L, [1.0, 2.0, 3.0, 4.0], [5.0, 5.0, 5.0, 5.0])
    expected = math.sqrt(2.5) / math.sqrt(30.0)
    assert r["commutator_M"] == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# Cycle 2 - descriptor fold
# ---------------------------------------------------------------------------


def test_fold_descriptor_hand_case():
    f_x = np.eye(2)
    f_y = np.array([[1.0, 0.0], [0.0, 2.0]])
    g_x = np.array([[0.5, 0.0], [0.0, 0.25]])
    g_y = np.array([[4.0, 0.0], [0.0, 8.0]])
    out = fold_descriptor(f_x, f_y, g_x, g_y)
    assert out["ok"] is True
    # f_y g_y^-1 g_x = diag(1*0.25*0.5, 2*0.125*0.25)
    #                 = diag(0.125, 0.0625).
    # A = I - that = diag(1 - 0.125, 1 - 0.0625) = diag(0.875, 0.9375).
    expected = np.diag([0.875, 0.9375])
    assert np.allclose(out["A"], expected, atol=1e-12)


def test_fold_descriptor_singular_g_y_reports_failure():
    f_x = np.eye(2)
    f_y = np.eye(2)
    g_x = np.eye(2)
    g_y = np.array([[1.0, 0.0], [0.0, 0.0]])
    out = fold_descriptor(f_x, f_y, g_x, g_y)
    assert out["ok"] is False
    assert out["A"] is None