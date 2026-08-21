#!/usr/bin/env python3
"""Numerical/symbolic sanity checks for the VSG theory audit.

This script verifies only mathematical examples and synthetic scaling laws.
It does NOT reproduce or fabricate any manuscript experiment.

Outputs
-------
- data/audit_numeric_results.json
- data/high_frequency_expansion.csv
- data/signed_probe_synthetic.csv
- data/dae_jacobian_check.csv
- data/approximate_separation_bound.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable, Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from scipy.linalg import expm


def projectors(n: int) -> Tuple[np.ndarray, np.ndarray]:
    if n < 2:
        raise ValueError("n must be at least 2")
    one = np.ones((n, 1), dtype=float)
    pc = one @ one.T / n
    return pc, np.eye(n) - pc


def complete_laplacian(n: int) -> np.ndarray:
    return n * np.eye(n) - np.ones((n, n))


def transfer_omega_w(
    M: np.ndarray,
    D: np.ndarray,
    L: np.ndarray,
    s: complex,
    omega_n: float = 1.0,
) -> np.ndarray:
    H = (s**2) * M + s * D + omega_n * L
    return s * np.linalg.inv(H)


def fro(A: np.ndarray) -> float:
    return float(np.linalg.norm(A, ord="fro"))


def max_cross_norms(
    M: np.ndarray,
    D: np.ndarray,
    L: np.ndarray,
    samples: Iterable[complex],
) -> Tuple[float, float]:
    pc, pd = projectors(M.shape[0])
    right = 0.0
    left = 0.0
    for s in samples:
        G = transfer_omega_w(M, D, L, s)
        right = max(right, fro(pd @ G @ pc))
        left = max(left, fro(pc @ G @ pd))
    return right, left


def decoder(a: np.ndarray | float) -> np.ndarray:
    a_arr = np.asarray(a, dtype=float)
    return np.where(a_arr >= 0.0, 600.0 * a_arr, 200.0 * a_arr)


def loglog_order(eps: np.ndarray, values: np.ndarray) -> float:
    eps = np.asarray(eps, dtype=float)
    values = np.abs(np.asarray(values, dtype=float))
    mask = (eps > 0.0) & (values > 0.0) & np.isfinite(values)
    if np.count_nonzero(mask) < 2:
        return float("nan")
    slope, _ = np.polyfit(np.log(eps[mask]), np.log(values[mask]), 1)
    return float(slope)


def finite_difference_jacobian(
    f: Callable[[np.ndarray], np.ndarray], x0: np.ndarray, h: float = 1e-7
) -> np.ndarray:
    x0 = np.asarray(x0, dtype=float)
    y0 = np.asarray(f(x0), dtype=float)
    J = np.zeros((y0.size, x0.size), dtype=float)
    for j in range(x0.size):
        e = np.zeros_like(x0)
        e[j] = 1.0
        J[:, j] = (f(x0 + h * e) - f(x0 - h * e)) / (2.0 * h)
    return J


def run_audit(output_dir: Path) -> Dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    samples = [0.7 + 0.4j, 1.0 + 0.0j, 2.0 + 1.5j, 10.0 + 3.0j]
    n = 4
    pc, p_d = projectors(n)
    L_bal = complete_laplacian(n)

    results: Dict[str, object] = {
        "notice": (
            "All values in this file are theorem checks, counterexamples, or synthetic "
            "diagnostics. They are not manuscript experiment results."
        )
    }

    # A1: exact separation for homogeneous diagonal M and D.
    M_h = 2.0 * np.eye(n)
    D_h = 3.0 * np.eye(n)
    r_h, l_h = max_cross_norms(M_h, D_h, L_bal, samples)
    results["task_A_homogeneous_balanced"] = {
        "max_norm_Pd_G_Pc": r_h,
        "max_norm_Pc_G_Pd": l_h,
        "expected": "both are numerical zero",
    }

    # A2: directed row-Laplacian, strongly connected but unbalanced.
    L_dir = np.array(
        [
            [1.0, -1.0, 0.0, 0.0],
            [0.0, 2.0, -2.0, 0.0],
            [0.0, 0.0, 3.0, -3.0],
            [-4.0, 0.0, 0.0, 4.0],
        ]
    )
    r_dir, l_dir = max_cross_norms(M_h, D_h, L_dir, samples)
    results["task_A_directed_unbalanced"] = {
        "L_times_1_norm": float(np.linalg.norm(L_dir @ np.ones(n))),
        "1T_times_L_norm": float(np.linalg.norm(np.ones(n) @ L_dir)),
        "max_norm_Pd_G_Pc": r_dir,
        "max_norm_Pc_G_Pd": l_dir,
        "interpretation": (
            "With scalar M,D and L1=0, common input remains common; lack of left balance "
            "allows differential input to leak into the common output."
        ),
    }

    # A3: rank-deficient differential output hides heterogeneity.
    M_rank = np.diag([1.0, 1.0, 2.0, 3.0])
    D_rank = np.diag([0.8, 0.8, 1.5, 2.1])
    C_d = np.array([[1.0, -1.0, 0.0, 0.0]]) / np.sqrt(2.0)
    hidden = 0.0
    full = 0.0
    for s in samples:
        G = transfer_omega_w(M_rank, D_rank, L_bal, s)
        hidden = max(hidden, fro(C_d @ G @ pc))
        full = max(full, fro(p_d @ G @ pc))
    results["task_A_rank_deficient_output"] = {
        "C_d_rank": int(np.linalg.matrix_rank(C_d)),
        "full_differential_dimension": n - 1,
        "max_norm_Cd_G_Pc": hidden,
        "max_norm_Pd_G_Pc": full,
        "interpretation": (
            "The measured difference omega_1-omega_2 is exactly blind to heterogeneity "
            "in the permutation-symmetric hidden subspace."
        ),
    }

    # A3b: checking only one frequency cannot establish the rational identity.
    M_onefreq = np.diag([1.0, 2.0, 3.0, 4.0])
    D_onefreq = np.diag([4.0, 3.0, 2.0, 1.0])
    G_at_1 = transfer_omega_w(M_onefreq, D_onefreq, L_bal, 1.0 + 0.0j)
    G_at_2 = transfer_omega_w(M_onefreq, D_onefreq, L_bal, 2.0 + 0.0j)
    results["task_A_single_frequency_counterexample"] = {
        "norm_Pd_G1_Pc": fro(p_d @ G_at_1 @ pc),
        "norm_Pc_G1_Pd": fro(pc @ G_at_1 @ p_d),
        "norm_Pd_G2_Pc": fro(p_d @ G_at_2 @ pc),
        "norm_Pc_G2_Pd": fro(pc @ G_at_2 @ p_d),
        "M_diagonal": np.diag(M_onefreq).tolist(),
        "D_diagonal": np.diag(D_onefreq).tolist(),
        "interpretation": (
            "At s=1, M_i+D_i is constant, so separation holds at that single frequency; "
            "it fails at s=2. A frequency grid is not the rational identity."
        ),
    }

    # A4: diagonality is essential for concluding M=mI and D=dI.
    M_dense = 1.2 * pc + 2.3 * p_d
    D_dense = 0.7 * pc + 1.9 * p_d
    L_dense = 4.0 * p_d
    r_dense, l_dense = max_cross_norms(M_dense, D_dense, L_dense, samples)
    results["task_A_nondiagonal_counterexample"] = {
        "max_norm_Pd_G_Pc": r_dense,
        "max_norm_Pc_G_Pd": l_dense,
        "distance_M_from_scalar_I": fro(M_dense - np.trace(M_dense) / n * np.eye(n)),
        "distance_D_from_scalar_I": fro(D_dense - np.trace(D_dense) / n * np.eye(n)),
        "interpretation": (
            "General dense M,D may be block diagonal in common/differential coordinates "
            "without being scalar multiples of I."
        ),
    }

    # A5: verify the first two Laurent coefficients and O(s^-3) remainder.
    M_l = np.diag([1.0, 1.7, 2.4, 3.2])
    D_l = np.diag([0.6, 1.0, 1.8, 2.5])
    Minv = np.linalg.inv(M_l)
    c1 = Minv
    c2 = -Minv @ D_l @ Minv
    hf_rows = []
    for sval in [25.0, 50.0, 100.0, 200.0, 400.0, 800.0]:
        G = transfer_omega_w(M_l, D_l, L_bal, complex(sval))
        approx1 = c1 / sval
        approx2 = c1 / sval + c2 / (sval**2)
        hf_rows.append(
            {
                "s": sval,
                "error_after_s_minus_1": fro(G - approx1),
                "error_after_s_minus_2": fro(G - approx2),
                "scaled_s2_error_after_first": (sval**2) * fro(G - approx1),
                "scaled_s3_error_after_second": (sval**3) * fro(G - approx2),
            }
        )
    hf_df = pd.DataFrame(hf_rows)
    hf_df.to_csv(output_dir / "high_frequency_expansion.csv", index=False)
    results["task_A_high_frequency"] = {
        "estimated_order_error_after_first_term": loglog_order(
            hf_df["s"].to_numpy(), hf_df["error_after_s_minus_1"].to_numpy()
        )
        * -1.0,
        "estimated_order_error_after_second_term": loglog_order(
            hf_df["s"].to_numpy(), hf_df["error_after_s_minus_2"].to_numpy()
        )
        * -1.0,
        "coefficient_1": c1.tolist(),
        "coefficient_2": c2.tolist(),
    }

    # A6/E9: sanity check for the approximate block-separation resolvent bound.
    perturb = np.array(
        [
            [0.0, 1.0, -0.5, 0.0],
            [-0.2, 0.0, 0.0, 0.3],
            [0.1, -0.4, 0.0, 0.0],
            [0.0, 0.2, -0.1, 0.0],
        ]
    )
    L_approx = L_bal + 0.08 * perturb
    approx_rows = []
    for sval in [0.8 + 0.4j, 2.0 + 1.0j, 5.0 + 2.0j]:
        H = (sval**2) * M_h + sval * D_h + L_approx
        H0 = pc @ H @ pc + p_d @ H @ p_d
        Eblock = pc @ H @ p_d + p_d @ H @ pc
        H0_inv = np.linalg.inv(H0)
        contraction = float(np.linalg.norm(H0_inv @ Eblock, ord=2))
        G = sval * np.linalg.inv(H)
        cross_right = float(np.linalg.norm(p_d @ G @ pc, ord=2))
        cross_left = float(np.linalg.norm(pc @ G @ p_d, ord=2))
        if contraction >= 1.0:
            bound = float("inf")
        else:
            bound = float(
                abs(sval)
                * np.linalg.norm(H0_inv, ord=2) ** 2
                * np.linalg.norm(Eblock, ord=2)
                / (1.0 - contraction)
            )
        approx_rows.append(
            {
                "s_real": float(np.real(sval)),
                "s_imag": float(np.imag(sval)),
                "norm_H0inv_E": contraction,
                "cross_right_2norm": cross_right,
                "cross_left_2norm": cross_left,
                "resolvent_upper_bound": bound,
                "bound_dominates_both": bool(max(cross_right, cross_left) <= bound * (1 + 1e-12)),
            }
        )
    approx_df = pd.DataFrame(approx_rows)
    approx_df.to_csv(output_dir / "approximate_separation_bound.csv", index=False)
    results["task_E_approximate_separation_bound"] = {
        "max_contraction_factor": float(approx_df["norm_H0inv_E"].max()),
        "all_cross_norms_below_bound": bool(approx_df["bound_dominates_both"].all()),
        "notice": "Numerical sanity check of the perturbation inequality, not plant data.",
    }

    # B: continuous-time and sampled-data first-order authority checks.
    A0 = np.array([[-0.9, 0.2], [-0.1, -0.7]])
    A1 = np.array([[0.5, -0.4], [0.3, 0.2]])
    A2 = np.array([[-0.2, 0.1], [0.6, -0.3]])
    Kappa = np.array([[0.7, -0.2], [0.1, 0.5]])

    def kappa(x: np.ndarray) -> np.ndarray:
        return Kappa @ x

    def A_of_u(u: np.ndarray) -> np.ndarray:
        return A0 + u[0] * A1 + u[1] * A2

    def f_mult(x: np.ndarray) -> np.ndarray:
        return A_of_u(kappa(x)) @ x

    J_mult = finite_difference_jacobian(f_mult, np.zeros(2))
    Badd = np.array([[1.0, 0.2], [-0.3, 0.8]])

    def f_add(x: np.ndarray) -> np.ndarray:
        return A0 @ x + Badd @ kappa(x)

    J_add = finite_difference_jacobian(f_add, np.zeros(2))
    T = 0.2

    def sampled_map(x: np.ndarray) -> np.ndarray:
        return expm(A_of_u(kappa(x)) * T) @ x

    J_sampled = finite_difference_jacobian(sampled_map, np.zeros(2))
    results["task_B_first_order_authority"] = {
        "continuous_multiplicative_error_norm": fro(J_mult - A0),
        "continuous_additive_error_norm": fro(J_add - (A0 + Badd @ Kappa)),
        "sampled_multiplicative_error_norm": fro(J_sampled - expm(A0 * T)),
        "A_u0": A0.tolist(),
        "A_additive_closed_loop": (A0 + Badd @ Kappa).tolist(),
        "sampled_A_u0": expm(A0 * T).tolist(),
    }

    # C: synthetic signed-probe order diagnostics.
    eps = 2.0 ** (-np.arange(2, 14, dtype=float))
    h_plus = decoder(eps)
    h_minus = decoder(-eps)
    decoder_odd = 0.5 * (h_plus - h_minus)
    decoder_even = 0.5 * (h_plus + h_minus)

    def first_order_mode(t: np.ndarray) -> np.ndarray:
        return np.where(t >= 0.0, 2.0 * t, 0.5 * t)

    def nonsmooth_quadratic(t: np.ndarray) -> np.ndarray:
        return np.where(t >= 0.0, 3.0 * t**2, 1.0 * t**2)

    def smooth_cubic(t: np.ndarray) -> np.ndarray:
        return 2.0 * t**2 + 0.75 * t**3

    first_odd = 0.5 * (first_order_mode(eps) - first_order_mode(-eps))
    quad_odd = 0.5 * (nonsmooth_quadratic(eps) - nonsmooth_quadratic(-eps))
    cubic_odd = 0.5 * (smooth_cubic(eps) - smooth_cubic(-eps))

    scaling_df = pd.DataFrame(
        {
            "epsilon": eps,
            "decoder_odd_raw": decoder_odd,
            "decoder_even_raw": decoder_even,
            "first_order_mode_odd": first_odd,
            "nonsmooth_quadratic_odd": quad_odd,
            "smooth_cubic_odd": cubic_odd,
            "decoder_odd_over_epsilon": decoder_odd / eps,
            "quadratic_odd_over_epsilon2": quad_odd / eps**2,
            "cubic_odd_over_epsilon3": cubic_odd / eps**3,
        }
    )
    scaling_df.to_csv(output_dir / "signed_probe_synthetic.csv", index=False)
    results["task_C_signed_probe"] = {
        "decoder_B_derivative_positive": 600.0,
        "decoder_B_derivative_negative": 200.0,
        "decoder_Clarke_generalized_Jacobian": [200.0, 600.0],
        "estimated_order_decoder_odd": loglog_order(eps, decoder_odd),
        "estimated_order_first_order_mode_odd": loglog_order(eps, first_odd),
        "estimated_order_nonsmooth_quadratic_odd": loglog_order(eps, quad_odd),
        "estimated_order_smooth_cubic_odd": loglog_order(eps, cubic_odd),
        "notice": "Synthetic functions illustrate orders only; they are not VSG outcomes.",
    }

    # E: index-1 DAE reduction and action-through-algebraic-equation example.
    Fx = np.array([[-1.0, 0.3], [0.2, -0.7]])
    Fy = np.array([[1.2], [-0.4]])
    Fu = np.zeros((2, 1))
    Gx = np.array([[0.5, -0.3]])
    Gy = np.array([[2.0]])
    Gu = np.array([[1.5]])
    Gy_inv = np.linalg.inv(Gy)
    Ared = Fx - Fy @ Gy_inv @ Gx
    Bred = Fu - Fy @ Gy_inv @ Gu
    K_dae = np.array([[0.4, -0.2]])
    Acl = Ared + Bred @ K_dae

    def dae_reduced_closed_loop(x: np.ndarray) -> np.ndarray:
        u = K_dae @ x
        y = -Gy_inv @ (Gx @ x + Gu @ u)
        return Fx @ x + Fy @ y + Fu @ u

    J_dae_fd = finite_difference_jacobian(dae_reduced_closed_loop, np.zeros(2))

    # Direct algebraic-measurement feedback u=Kx*x+Ky*y.
    Kx = np.array([[0.35, -0.15]])
    Ky = np.array([[0.25]])
    closed_alg = Gy + Gu @ Ky
    Acl_y = (
        Fx
        + Fu @ Kx
        - (Fy + Fu @ Ky) @ np.linalg.inv(closed_alg) @ (Gx + Gu @ Kx)
    )

    def dae_algebraic_measurement_feedback(x: np.ndarray) -> np.ndarray:
        y = -np.linalg.inv(closed_alg) @ ((Gx + Gu @ Kx) @ x)
        u = Kx @ x + Ky @ y
        return Fx @ x + Fy @ y + Fu @ u

    J_dae_y_fd = finite_difference_jacobian(
        dae_algebraic_measurement_feedback, np.zeros(2)
    )

    dae_rows = []
    for name, mat in {
        "A_reduced": Ared,
        "B_u_reduced": Bred,
        "A_closed_loop_state_feedback": Acl,
        "A_closed_loop_state_feedback_finite_difference": J_dae_fd,
        "A_closed_loop_algebraic_measurement": Acl_y,
        "A_closed_loop_algebraic_measurement_finite_difference": J_dae_y_fd,
    }.items():
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                dae_rows.append({"matrix": name, "row": i, "col": j, "value": mat[i, j]})
    pd.DataFrame(dae_rows).to_csv(output_dir / "dae_jacobian_check.csv", index=False)
    results["task_E_DAE"] = {
        "sigma_min_g_y": float(np.linalg.svd(Gy, compute_uv=False)[-1]),
        "sigma_min_closed_algebraic_jacobian": float(
            np.linalg.svd(closed_alg, compute_uv=False)[-1]
        ),
        "A_reduced": Ared.tolist(),
        "B_u_reduced": Bred.tolist(),
        "A_closed_loop_state_feedback": Acl.tolist(),
        "state_feedback_finite_difference_error_norm": fro(J_dae_fd - Acl),
        "A_closed_loop_algebraic_measurement": Acl_y.tolist(),
        "algebraic_measurement_finite_difference_error_norm": fro(J_dae_y_fd - Acl_y),
        "key_point": (
            "Although f_u=0, g_u != 0 and f_y != 0 create nonzero additive first-order "
            "authority B_u,reduced = -f_y g_y^{-1} g_u. Direct y feedback additionally "
            "changes the closed algebraic Jacobian to g_y+g_u K_y."
        ),
    }

    with (output_dir / "audit_numeric_results.json").open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
        help="Directory for generated CSV/JSON files.",
    )
    args = parser.parse_args()
    results = run_audit(args.output_dir)
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()


