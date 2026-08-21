#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
from scipy.linalg import expm

from math_blueprints import (
    closed_loop_transfer_sensitivity,
    commutator,
    fractional_zoh_split,
    mixed_partial_vector,
    project_slew,
    projector_common,
    resolvent_commutator_identity,
    zoh_integral,
)


def test_slew_alias() -> None:
    assert np.allclose(project_slew([1.0], [0.0], 0.25), [0.75])
    assert np.allclose(project_slew([-1.0], [0.0], 0.25), [-0.75])
    assert np.allclose(project_slew([-1.0], [1.0], 0.25), [-0.75])


def test_fractional_split() -> None:
    a = np.array([[-0.4, 0.2], [0.0, -0.1]])
    b = np.array([[1.0], [0.5]])
    ts = 0.2
    for delta in (0.0, 0.03, 0.1, 0.199999):
        ad, b0, b1 = fractional_zoh_split(a, b, ts, delta)
        assert np.allclose(ad, expm(a * ts), atol=1e-13)
        assert np.allclose(b0 + b1, zoh_integral(a, b, ts), atol=1e-13)


def test_commutator_identity() -> None:
    a = np.array([[-0.2, 0.3], [0.1, -0.5]])
    p = projector_common(2)
    left, right = resolvent_commutator_identity(a, p, 0.7j)
    assert np.allclose(left, right, atol=1e-12)
    assert np.linalg.norm(commutator(a, p)) > 0


def test_mixed_partial() -> None:
    n = np.array([[2.0, -1.0], [0.5, 3.0]])

    def field(x: np.ndarray, u: np.ndarray, w: np.ndarray) -> np.ndarray:
        del w
        return u[0] * (n @ x)

    v = np.array([0.4, -0.7])
    estimate = mixed_partial_vector(
        field,
        state_direction=v,
        action_index=0,
        state_step=1e-4,
        action_step=2e-4,
        action_dim=1,
    )
    assert np.allclose(estimate, n @ v, rtol=1e-9, atol=1e-10)


def test_transfer_sensitivity() -> None:
    # Scalar plant, embedded as 1x1 arrays. Check total derivative by finite difference.
    rho = 0.0
    z = np.exp(1j * 0.4)

    def arrays(r: float):
        a = np.array([[0.7 + 0.04 * r]])
        bc = np.array([[0.2 - 0.01 * r]])
        bw = np.array([[0.5 + 0.02 * r]])
        c = np.array([[1.1 + 0.03 * r]])
        dc = np.array([[0.0]])
        dw = np.array([[0.0]])
        k = np.array([[0.8 - 0.05 * r]])
        return a, bc, bw, c, dc, dw, k

    a, bc, bw, c, dc, dw, k = arrays(rho)
    result = closed_loop_transfer_sensitivity(
        z=z,
        a=a,
        b_c=bc,
        b_w=bw,
        c=c,
        d_c=dc,
        d_w=dw,
        k=k,
        a_rho=np.array([[0.04]]),
        b_c_rho=np.array([[-0.01]]),
        b_w_rho=np.array([[0.02]]),
        c_rho=np.array([[0.03]]),
        d_c_rho=np.array([[0.0]]),
        d_w_rho=np.array([[0.0]]),
        k_rho=np.array([[-0.05]]),
    )
    h = 1e-6

    def g_at(r: float) -> np.ndarray:
        aa, bcc, bww, cc, dcc, dww, kk = arrays(r)
        pc = cc @ np.linalg.solve(z * np.eye(1) - aa, bcc) + dcc
        pw = cc @ np.linalg.solve(z * np.eye(1) - aa, bww) + dww
        return np.linalg.solve(np.eye(1) + pc @ kk, pw)

    fd = (g_at(h) - g_at(-h)) / (2 * h)
    assert np.allclose(result.g_rho, fd, rtol=2e-8, atol=2e-9)


def main() -> int:
    test_slew_alias()
    test_fractional_split()
    test_commutator_identity()
    test_mixed_partial()
    test_transfer_sensitivity()
    print("all blueprint tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
