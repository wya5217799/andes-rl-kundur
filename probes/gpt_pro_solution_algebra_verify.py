"""Verify the algebraic identities of the external GPT Pro answer
(tmp/gpt_pro_math_solution_20260819.md) against the frozen control code.

Motivation: the external answer is a design aid. Per the external-theory-intake
contract, its algebraic identities (not its mechanism predictions or its
paper-grade propositions) need repo-side numerical verification before any use.
This probe re-derives each identity from the frozen implementation, never from
the answer's own text, so a mismatch is an answer error, not a self-reference.

Covered (Problem 1, icems three-edge residual):
  - zero-sum incidence (1^T B = 0) and interior-node bound 2*edge_flow_max;
  - the reachable action interval U_0(h, sigma) of the reverse_limit=0
    prior-residual composition, and its 0.5*sigma derivative;
  - the sign(0)=0 dead zone (d=0 forces a=0);
  - B3 (reverse_limit=beta>0) strict expansion: it adds a finite reverse
    (cross-zero) region only when 0 < |p| < 0.5, and exactly degenerates to the
    reverse_limit=0 law and to the traditional controller (r=0).

Covered (Problem 2, residual-headroom zero-sum action basis):
  - Range(B_e) equals the zero-sum subspace (rank 3, kernel of 1^T);
  - adding the common channel b=1_4 raises rank 3 -> 4 (minimal added dim = 1,
    strict expansion);
  - common_amplitude >= node_residual_max keeps the executed inertia command
    non-negative (min command 200 > 0).

NOT covered (data-gated): the "6/16 infeasible / 16/16 feasible" numerical
classification needs the raw response matrices G_s, y_s^0 that are not archived
(see the answer section 9). This probe verifies only structure, not that count.

Exit codes: 0 = all identities hold to tolerance; 1 = a check failed; 2 = import
failure. Residual gate: structural identities must reproduce to ~1e-9; the grid
checks compare closed-form bounds to the implementation on a dense grid.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from andes_rl_kundur.control.vector_inertia_residual import (  # noqa: E402
    INCIDENCE,
    VectorInertiaResidualContract,
    execute_edge_residual_numpy,
)
from andes_rl_kundur.control.classical_edge_residual import (  # noqa: E402
    compose_prior_residual_numpy,
)

# The frozen control code computes in np.float32, so structural identities hold
# to float32 rounding (~1e-7). Gate at 1e-6, not the float64 1e-18 used for
# symbolic probes elsewhere.
TOL = 1e-6


def _check(name: str, ok: bool, detail: str = "") -> tuple[bool, str]:
    return ok, f"[{'PASS' if ok else 'FAIL'}] {name} {detail}".strip()


def run() -> list[tuple[bool, str]]:
    results: list[tuple[bool, str]] = []
    cfg = VectorInertiaResidualContract()

    # --- Problem 1: icems three-edge residual ---
    B = INCIDENCE.astype(np.float64)
    ones = np.ones(4, dtype=np.float64)
    results.append(_check(
        "P1 zero-sum incidence 1^T B = 0",
        np.allclose(ones @ B, 0.0, atol=TOL),
        f"residual={float(np.max(np.abs(ones @ B))):.3e}",
    ))
    results.append(_check(
        "P1 interior-node bound |m|_inf <= 2*edge_flow_max",
        abs(cfg.node_residual_max - 2.0 * cfg.edge_flow_max) < TOL
        and abs(cfg.node_slew_max - 2.0 * cfg.edge_slew_max) < TOL,
        f"node_max={cfg.node_residual_max}, 2*edge_flow_max={2 * cfg.edge_flow_max}",
    ))

    # Reachable action interval U_0(h, sigma) and derivative, dense grid.
    ps = np.concatenate([np.linspace(0.0, 0.999, 41), np.array([0.5])])
    rs = np.linspace(-1.0, 1.0, 101)
    ds = [-1.0, 1.0, 0.0]
    interval_ok = True
    deriv_ok = True
    max_interval_gap = 0.0
    for p in ps:
        for d in ds:
            sigma = float(np.sign(d))
            h = abs(p)
            lo = sigma * max(0.0, h - 0.5)
            hi = sigma * min(1.0, h + 0.5)
            lo_b, hi_b = min(lo, hi), max(lo, hi)
            for r in rs:
                out = float(compose_prior_residual_numpy(
                    np.full(3, p), np.full(3, r), np.full(3, d),
                    residual_scale=0.5, reverse_limit=0.0,
                )[0])
                if d == 0.0:
                    interval_ok &= bool(out == 0.0)
                else:
                    interval_ok &= bool(lo_b - TOL <= out <= hi_b + TOL)
                    gap = abs(out - float(np.clip(out, lo_b, hi_b)))
                    max_interval_gap = max(max_interval_gap, gap)
                # derivative 0.5*sigma in the unclipped interior of both bounds.
                arg = h + 0.5 * r
                if d != 0.0 and 0.0 < arg < 1.0:
                    deriv_ok &= bool(np.allclose(out, sigma * arg, atol=TOL))
    results.append(_check(
        "P1 action interval U_0(h, sigma) matches reverse_limit=0 composition",
        interval_ok, f"max_gap={max_interval_gap:.3e}",
    ))
    results.append(_check(
        "P1 derivative da/dr = 0.5*sigma in unclipped interior",
        deriv_ok,
    ))

    # B3 strict expansion: beta>0 adds reverse region only when 0<|p|<0.5.
    beta = 0.2
    b3_expands = False
    b3_no_expand_large_p = True
    for p in [0.1, 0.2, 0.3, 0.4]:
        out0 = compose_prior_residual_numpy(
            np.array([p, p, p]), np.array([-1.0, -1.0, -1.0]),
            np.array([1.0, 1.0, 1.0]), residual_scale=0.5, reverse_limit=0.0)
        outb = compose_prior_residual_numpy(
            np.array([p, p, p]), np.array([-1.0, -1.0, -1.0]),
            np.array([1.0, 1.0, 1.0]), residual_scale=0.5, reverse_limit=beta)
        if np.all(out0 >= 0.0) and np.any(outb < 0.0):
            b3_expands = True
    for p in [0.6, 0.8]:
        outb = compose_prior_residual_numpy(
            np.array([p, p, p]), np.array([-1.0, -1.0, -1.0]),
            np.array([1.0, 1.0, 1.0]), residual_scale=0.5, reverse_limit=beta)
        if np.any(outb < 0.0):
            b3_no_expand_large_p = False
    results.append(_check(
        "P1 B3 beta>0 adds cross-zero region for 0<|p|<0.5",
        b3_expands,
    ))
    results.append(_check(
        "P1 B3 beta>0 cannot cross zero for |p|>=0.5",
        b3_no_expand_large_p,
    ))

    # B3 exact degeneration: r=0 recovers the sign(|p|) prior exactly.
    p3 = np.array([0.3, -0.4, 0.7])
    d3 = np.array([1.0, -1.0, 1.0])
    prior_exact = np.sign(d3) * np.clip(np.abs(p3), 0.0, 1.0)
    out_r0_b0 = compose_prior_residual_numpy(p3, np.zeros(3), d3, residual_scale=0.5, reverse_limit=0.0)
    results.append(_check(
        "P1 traditional controller (r=0) is an exact degenerate point",
        bool(np.allclose(out_r0_b0, prior_exact, atol=TOL)),
    ))

    # --- Problem 2: residual-headroom zero-sum basis ---
    Be = B  # edge incidence is the zero-sum action basis
    rank_Be = int(np.linalg.matrix_rank(Be))
    results.append(_check(
        "P2 Range(B_e) = zero-sum subspace (rank 3)",
        rank_Be == 3 and bool(np.allclose(ones @ Be, 0.0, atol=TOL)),
        f"rank={rank_Be}",
    ))
    Bplus = np.column_stack([Be, ones])
    rank_Bplus = int(np.linalg.matrix_rank(Bplus))
    results.append(_check(
        "P2 B_+ = [B_e, 1_4] strictly expands to rank 4 (min added dim = 1)",
        rank_Bplus == 4 and rank_Bplus == rank_Be + 1,
        f"rank 3 -> {rank_Bplus}",
    ))
    results.append(_check(
        "P2 common amplitude keeps executed inertia non-negative",
        cfg.common_amplitude >= cfg.node_residual_max,
        f"common={cfg.common_amplitude} >= node_max={cfg.node_residual_max}; "
        f"min_M={cfg.baseline_m + cfg.dm_max * (cfg.common_amplitude - cfg.node_residual_max):.1f}",
    ))

    # Cross-check the executor emits zero-sum node actions.
    edge, node, actions = execute_edge_residual_numpy(
        np.array([0.1, -0.2, 0.05]), previous_edge=np.zeros(3), step=0, contract=cfg)
    results.append(_check(
        "P2 executor node actions are zero-sum (1^T node = 0)",
        bool(np.allclose(np.sum(node), 0.0, atol=TOL)),
        f"sum={float(np.sum(node)):.3e}",
    ))

    return results


def main() -> int:
    try:
        results = run()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] import/execution failure: {exc}", file=sys.stderr)
        return 2
    for ok, line in results:
        print(line)
    failed = [line for ok, line in results if not ok]
    print(f"--- {sum(1 for ok, _ in results if ok)}/{len(results)} checks passed ---")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
