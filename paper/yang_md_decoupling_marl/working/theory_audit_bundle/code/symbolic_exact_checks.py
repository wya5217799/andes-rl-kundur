#!/usr/bin/env python3
"""Exact SymPy checks supporting the VSG theory audit.

The calculations use rational arithmetic and symbolic ``s`` where practical.
They verify theorem coefficients and counterexample identities only. They do not
represent simulations or empirical results for the manuscript.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import sympy as sp


def is_zero_matrix(M: sp.MatrixBase) -> bool:
    return all(sp.simplify(v) == 0 for v in M)


def matrix_strings(M: sp.MatrixBase) -> list[list[str]]:
    return [[str(sp.factor(M[i, j])) for j in range(M.cols)] for i in range(M.rows)]


def scalar_strings(values: list[Any]) -> list[str]:
    return [str(sp.factor(v)) for v in values]


def run_exact_checks() -> dict[str, Any]:
    n = 4
    s = sp.symbols("s")
    I = sp.eye(n)
    one = sp.ones(n, 1)
    Pc = one * one.T / sp.Integer(n)
    Pd = I - Pc
    L_bal = n * I - one * one.T

    out: dict[str, Any] = {
        "notice": (
            "Exact symbolic theorem/counterexample checks only; not manuscript "
            "experiment data."
        )
    }

    # Task A: Laurent coefficients for diagonal M,D.
    m = sp.symbols("m1:5", nonzero=True)
    d = sp.symbols("d1:5")
    Minv = sp.diag(*[1 / mi for mi in m])
    D = sp.diag(*d)
    c1 = Minv
    c2 = -Minv * D * Minv
    right_c1 = sp.simplify(Pd * c1 * Pc)
    right_c2 = sp.simplify(Pd * c2 * Pc)
    out["task_A_laurent_coefficients"] = {
        "coefficient_s_minus_1": matrix_strings(c1),
        "coefficient_s_minus_2": matrix_strings(c2),
        "Pd_c1_Pc_times_1": scalar_strings(list(sp.simplify(Pd * c1 * one))),
        "Pd_c2_Pc_times_1": scalar_strings(list(sp.simplify(Pd * c2 * one))),
        "interpretation": (
            "Vanishing of the first vector makes 1/m_i equal; after that, "
            "vanishing of the second makes d_i equal."
        ),
        "right_c1_shape": list(right_c1.shape),
        "right_c2_shape": list(right_c2.shape),
    }

    # Directed row-balanced but not left-balanced example.
    L_dir = sp.Matrix(
        [
            [1, -1, 0, 0],
            [0, 2, -2, 0],
            [0, 0, 3, -3],
            [-4, 0, 0, 4],
        ]
    )
    H_dir = (2 * s**2 + 3 * s) * I + L_dir
    G_dir_at_1 = H_dir.subs(s, 1).inv()  # s=1, so G=H^{-1}.
    right_at_1 = sp.simplify(Pd * G_dir_at_1 * Pc)
    left_at_1 = sp.simplify(Pc * G_dir_at_1 * Pd)
    out["task_A_directed_unbalanced"] = {
        "L_times_1": scalar_strings(list(L_dir * one)),
        "1T_times_L": scalar_strings(list(one.T * L_dir)),
        "right_common_invariance_symbolic": bool(
            is_zero_matrix(H_dir * one - (2 * s**2 + 3 * s) * one)
        ),
        "Pd_G1_Pc_is_zero": bool(is_zero_matrix(right_at_1)),
        "Pc_G1_Pd_is_zero": bool(is_zero_matrix(left_at_1)),
        "Pc_G1_Pd": matrix_strings(left_at_1),
    }

    # Rank-deficient differential output hides a heterogeneous direction.
    M_rank = sp.diag(1, 1, 2, 3)
    D_rank = sp.diag(
        sp.Rational(4, 5),
        sp.Rational(4, 5),
        sp.Rational(3, 2),
        sp.Rational(21, 10),
    )
    C_d = sp.Matrix([[1, -1, 0, 0]])
    H_rank = s**2 * M_rank + s * D_rank + L_bal
    hidden_numerator = sp.simplify(C_d * H_rank.adjugate() * one)
    full_at_1 = sp.simplify(Pd * H_rank.subs(s, 1).inv() * Pc)
    out["task_A_rank_deficient_output"] = {
        "Cd_adjugate_H_times_1": matrix_strings(hidden_numerator),
        "Cd_G_Pc_rational_identity_is_zero": bool(is_zero_matrix(hidden_numerator)),
        "full_Pd_G1_Pc_is_zero": bool(is_zero_matrix(full_at_1)),
        "full_Pd_G1_Pc": matrix_strings(full_at_1),
    }

    # Heterogeneous M,D separate at one frequency only.
    M_one = sp.diag(1, 2, 3, 4)
    D_one = sp.diag(4, 3, 2, 1)
    H_one = s**2 * M_one + s * D_one + L_bal
    G1 = H_one.subs(s, 1).inv()
    G2 = 2 * H_one.subs(s, 2).inv()
    out["task_A_single_frequency"] = {
        "Pd_G1_Pc_is_zero": bool(is_zero_matrix(sp.simplify(Pd * G1 * Pc))),
        "Pc_G1_Pd_is_zero": bool(is_zero_matrix(sp.simplify(Pc * G1 * Pd))),
        "Pd_G2_Pc_is_zero": bool(is_zero_matrix(sp.simplify(Pd * G2 * Pc))),
        "Pd_G2_Pc": matrix_strings(sp.simplify(Pd * G2 * Pc)),
    }

    # Dense block-preserving M,D show why diagonality is essential.
    M_dense = sp.Rational(6, 5) * Pc + sp.Rational(23, 10) * Pd
    D_dense = sp.Rational(7, 10) * Pc + sp.Rational(19, 10) * Pd
    K_dense = 4 * Pd
    H_dense = s**2 * M_dense + s * D_dense + K_dense
    out["task_A_nondiagonal_block_preserving"] = {
        "M_commutes_with_Pc": bool(is_zero_matrix(sp.simplify(M_dense * Pc - Pc * M_dense))),
        "D_commutes_with_Pc": bool(is_zero_matrix(sp.simplify(D_dense * Pc - Pc * D_dense))),
        "K_commutes_with_Pc": bool(is_zero_matrix(sp.simplify(K_dense * Pc - Pc * K_dense))),
        "M_is_scalar_identity": False,
        "D_is_scalar_identity": False,
        "cross_at_s_1_is_zero": bool(
            is_zero_matrix(sp.simplify(Pd * H_dense.subs(s, 1).inv() * Pc))
        ),
    }

    # Task B: exact derivative for an affine A(u) and linear kappa.
    x1, x2 = sp.symbols("x1 x2")
    x = sp.Matrix([x1, x2])
    A0 = sp.Matrix([[sp.Rational(-9, 10), sp.Rational(1, 5)], [sp.Rational(-1, 10), sp.Rational(-7, 10)]])
    A1 = sp.Matrix([[sp.Rational(1, 2), sp.Rational(-2, 5)], [sp.Rational(3, 10), sp.Rational(1, 5)]])
    A2 = sp.Matrix([[sp.Rational(-1, 5), sp.Rational(1, 10)], [sp.Rational(3, 5), sp.Rational(-3, 10)]])
    Kappa = sp.Matrix([[sp.Rational(7, 10), sp.Rational(-1, 5)], [sp.Rational(1, 10), sp.Rational(1, 2)]])
    u = Kappa * x
    F_mult = (A0 + u[0] * A1 + u[1] * A2) * x
    J_mult = sp.simplify(F_mult.jacobian(x).subs({x1: 0, x2: 0}))
    Bp = sp.Matrix([[1, sp.Rational(1, 5)], [sp.Rational(-3, 10), sp.Rational(4, 5)]])
    F_add = A0 * x + Bp * u
    J_add = sp.simplify(F_add.jacobian(x).subs({x1: 0, x2: 0}))
    out["task_B_exact_jacobians"] = {
        "multiplicative_jacobian_equals_A0": bool(is_zero_matrix(J_mult - A0)),
        "multiplicative_jacobian": matrix_strings(J_mult),
        "additive_jacobian_equals_A0_plus_BK": bool(
            is_zero_matrix(J_add - (A0 + Bp * Kappa))
        ),
        "additive_jacobian": matrix_strings(J_add),
    }

    # Task C: exact one-sided decoder signed components.
    eps = sp.symbols("epsilon", positive=True)
    h_plus = 600 * eps
    h_minus = -200 * eps
    out["task_C_decoder"] = {
        "odd_component": str(sp.simplify((h_plus - h_minus) / 2)),
        "even_component": str(sp.simplify((h_plus + h_minus) / 2)),
        "positive_directional_gain": 600,
        "negative_directional_gain": 200,
        "Clarke_interval": [200, 600],
    }

    # Task E: exact Schur complement, including direct algebraic measurement feedback.
    Fx = sp.Matrix([[sp.Rational(-1), sp.Rational(3, 10)], [sp.Rational(1, 5), sp.Rational(-7, 10)]])
    Fy = sp.Matrix([[sp.Rational(6, 5)], [sp.Rational(-2, 5)]])
    Fu = sp.zeros(2, 1)
    Gx = sp.Matrix([[sp.Rational(1, 2), sp.Rational(-3, 10)]])
    Gy = sp.Matrix([[2]])
    Gu = sp.Matrix([[sp.Rational(3, 2)]])
    Kx_state = sp.Matrix([[sp.Rational(2, 5), sp.Rational(-1, 5)]])
    Ared = sp.simplify(Fx - Fy * Gy.inv() * Gx)
    Bred = sp.simplify(Fu - Fy * Gy.inv() * Gu)
    Acl_state = sp.simplify(Ared + Bred * Kx_state)

    Kx_y = sp.Matrix([[sp.Rational(7, 20), sp.Rational(-3, 20)]])
    Ky = sp.Matrix([[sp.Rational(1, 4)]])
    alg_closed = Gy + Gu * Ky
    Acl_y = sp.simplify(
        Fx
        + Fu * Kx_y
        - (Fy + Fu * Ky) * alg_closed.inv() * (Gx + Gu * Kx_y)
    )
    out["task_E_exact_DAE"] = {
        "A_reduced": matrix_strings(Ared),
        "B_u_reduced": matrix_strings(Bred),
        "B_u_reduced_is_nonzero_despite_f_u_zero": not is_zero_matrix(Bred),
        "A_closed_loop_state_feedback": matrix_strings(Acl_state),
        "closed_algebraic_jacobian": matrix_strings(alg_closed),
        "A_closed_loop_algebraic_measurement": matrix_strings(Acl_y),
    }

    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "symbolic_exact_results.json",
    )
    args = parser.parse_args()
    result = run_exact_checks()
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()


