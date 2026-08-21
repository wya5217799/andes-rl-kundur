"""Slice-3 tests: Kron reduction of the network B-block to the VSG buses.

Expected values are hand-derived from a three-bus chain with unit
susceptances; no implementation formula is reused in the tests.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest


from probes.homogenization_linearization import (  # noqa: E402
    check_reduced_l,
    kron_reduce_b_block,
)

# Three-bus chain 1-2-3 with unit susceptance edges; VSGs at buses 1 and 3.
B_CHAIN = np.array([
    [1.0, -1.0, 0.0],
    [-1.0, 2.0, -1.0],
    [0.0, -1.0, 1.0],
])


def test_kron_reduce_three_bus_chain_hand_value():
    # B_vv = [[1,0],[0,1]], B_vl = [[-1],[-1]], B_ll = [2], B_lv = [[-1,-1]]
    # L = B_vv - B_vl B_ll^-1 B_lv = [[0.5,-0.5],[-0.5,0.5]].
    l_red = kron_reduce_b_block(B_CHAIN, [0, 2])
    expected = np.array([[0.5, -0.5], [-0.5, 0.5]])
    assert np.allclose(l_red, expected, atol=1e-12)


def test_kron_reduce_all_vsg_returns_identity_reduction():
    l_red = kron_reduce_b_block(B_CHAIN, [0, 1, 2])
    assert np.allclose(l_red, B_CHAIN, atol=1e-12)


def test_check_reduced_l_accepts_hand_case():
    l_red = kron_reduce_b_block(B_CHAIN, [0, 2])
    out = check_reduced_l(l_red)
    assert out["ok"] is True
    assert out["symmetric"] is True
    assert out["right_balance"] == pytest.approx(0.0, abs=1e-12)
    assert out["left_balance"] == pytest.approx(0.0, abs=1e-12)


def test_check_reduced_l_rejects_asymmetric_matrix():
    bad = np.array([[0.5, -0.4], [-0.5, 0.5]])
    out = check_reduced_l(bad)
    assert out["ok"] is False
    assert out["symmetric"] is False


def test_check_reduced_l_rejects_unbalanced_matrix():
    bad = np.array([[0.6, -0.5], [-0.5, 0.5]])
    out = check_reduced_l(bad)
    assert out["ok"] is False
    assert out["right_balance"] > 0.0