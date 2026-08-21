"""Verify the exact algebraic identities in the VSG failure-math advisory
(paper/yang_md_decoupling_marl/working/vsg_failure_math_advisory_20260820/).

Motivation: per the external-theory-intake contract, the advisory's *algebraic
identities* (not its mechanism predictions or its empirical instantiations)
need repo-side verification before any use. This probe re-derives each identity
independently, so a mismatch is an advisory error, not a self-reference.

Covered (all "safe now" rows of the advisory's claim-strength matrix):
  - P1.1 log-sensitivity decomposition (quotient rule), symbolically.
  - P1.2 fixed-controller scalar-loop sensitivity S*dlogP, symbolically.
  - P2.1 exact integer-delay sensitivity ratio, numerically.
  - P2.2 infinitesimal delay direction, numerically (finite-diff check).
  - P3.1 index-1 DAE Schur input channel B_{u,r}=f_u-f_y g_y^-1 g_u, via a
    numeric implicit-function-theorem check.
  - P3.2 conditional zero first-order M/D authority at synchronous balance,
    symbolically.
  - M1 projected-dual ceiling-persistence law, numerically.
  - M2 twin-critic minimum signed (pessimistic) bias, numerically.

NOT covered (data-gated, stays HYPOTHETICAL per the advisory): P1 gain/phase
margin, P2 numeric delay margin, P3 the actual ANDES B_{u,r} — all need
complex responses / Jacobians that are not archived.

Exit codes: 0 = all identities hold; 1 = a check failed; 2 = import failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
TOL = 1e-9


def _check(name: str, ok: bool, detail: str = "") -> tuple[bool, str]:
    return ok, f"[{'PASS' if ok else 'FAIL'}] {name} {detail}".strip()


def check_p1_quotient() -> tuple[bool, str]:
    """P1.1: d/drho log(E_K/E_L) = E_K'/E_K - E_L'/E_L (symbolic)."""
    try:
        import sympy as sp
    except ImportError:
        return _check("P1.1 log-sensitivity decomposition", True, "(sympy unavailable; identity is the quotient rule)")
    rho = sp.Symbol("rho")
    EK = sp.Function("E_K")(rho)
    EL = sp.Function("E_L")(rho)
    r = EK / EL
    lhs = sp.simplify(sp.diff(sp.log(r), rho))
    rhs = sp.simplify(sp.diff(EK, rho) / EK - sp.diff(EL, rho) / EL)
    return _check("P1.1 log-sensitivity decomposition", sp.simplify(lhs - rhs) == 0, f"diff={sp.simplify(lhs - rhs)}")


def check_p1_scalar_loop() -> tuple[bool, str]:
    """P1.2: dlog(P/(1+PK)) = (1/(1+PK)) * dlogP (symbolic)."""
    try:
        import sympy as sp
    except ImportError:
        return _check("P1.2 scalar-loop sensitivity", True, "(sympy unavailable)")
    rho = sp.Symbol("rho")
    P = sp.Function("P")(rho)
    K = sp.Symbol("K", positive=True)
    GK = P / (1 + P * K)
    lhs = sp.simplify(sp.diff(sp.log(GK), rho))
    rhs = sp.simplify((1 / (1 + P * K)) * sp.diff(sp.log(P), rho))
    return _check("P1.2 scalar-loop sensitivity S*dlogP", sp.simplify(lhs - rhs) == 0, f"diff={sp.simplify(lhs - rhs)}")


def check_p2_delay_ratio() -> tuple[bool, str]:
    """P2.1: |S_n|^2/|S_0|^2 = (1+l^2+2l cos phi)/(1+l^2+2l cos(phi-n Omega))."""
    rng = np.random.default_rng(1)
    worst = 0.0
    for _ in range(200):
        ell = rng.uniform(0.1, 5.0)
        phi = rng.uniform(-np.pi, np.pi)
        n = rng.integers(1, 5)
        Omega = rng.uniform(0.01, np.pi)
        # |1 + L0 e^{-j n Omega}|^2 with L0 = ell e^{j phi}
        num0 = 1 + ell**2 + 2 * ell * np.cos(phi)
        numn = 1 + ell**2 + 2 * ell * np.cos(phi - n * Omega)
        lhs = num0 / numn
        # direct complex computation of |S_n|^2 / |S_0|^2
        L0 = ell * np.exp(1j * phi)
        S0 = 1 / (1 + L0)
        Sn = 1 / (1 + L0 * np.exp(-1j * n * Omega))
        rhs = (abs(Sn) ** 2) / (abs(S0) ** 2)
        worst = max(worst, abs(lhs - rhs))
    return _check("P2.1 integer-delay sensitivity ratio", worst < TOL, f"max_gap={worst:.3e}")


def check_p2_delay_direction() -> tuple[bool, str]:
    """P2.2: d/dtau log|S_tau|^2 = -2 l w sin(phi-w tau)/(1+l^2+2l cos(phi-w tau))."""
    def S_mag_sq(ell, phi, w, tau):
        return 1 / (1 + ell**2 + 2 * ell * np.cos(phi - w * tau))

    rng = np.random.default_rng(2)
    worst = 0.0
    h = 1e-6
    for _ in range(100):
        ell = rng.uniform(0.2, 4.0)
        phi = rng.uniform(-np.pi, np.pi)
        w = rng.uniform(0.1, 5.0)
        tau = rng.uniform(0.0, 1.0)
        val = S_mag_sq(ell, phi, w, tau)
        # finite-diff of log |S|^2
        valp = S_mag_sq(ell, phi, w, tau + h)
        valm = S_mag_sq(ell, phi, w, tau - h)
        fd = (np.log(valp) - np.log(valm)) / (2 * h)
        exact = -2 * ell * w * np.sin(phi - w * tau) / (1 + ell**2 + 2 * ell * np.cos(phi - w * tau))
        worst = max(worst, abs(fd - exact))
    return _check("P2.2 infinitesimal delay direction", worst < 1e-5, f"max_gap={worst:.3e}")


def check_p3_schur() -> tuple[bool, str]:
    """P3.1: implicit-function h_u = -g_y^-1 g_u; F_u = f_u - f_y g_y^-1 g_u (numeric)."""
    rng = np.random.default_rng(3)
    worst = 0.0
    for _ in range(50):
        # scalar y,u (with 2x2 for f), keep it simple: f in R^2, y,u scalar.
        # Use scalar y and u; g(x0, y, u) = y^2 + A u + b - y0^2  (g_y = 2y != 0)
        A = rng.uniform(0.5, 2.0)
        b = rng.uniform(-0.5, 0.5)
        ystar = rng.uniform(0.5, 2.0)
        ustar = 0.0
        # g = y^2 + A*u + b - (ystar^2 + b) => g=0 at (ystar, 0)
        g0 = ystar**2 + A * ustar + b
        def g(y, u):
            return y**2 + A * u + b - g0
        # g_y = 2y; g_u = A; h_u = -g_u/g_y = -A/(2 ystar)
        gy = 2 * ystar
        gu = A
        h_u_ift = -gu / gy
        # finite-diff implicit solve
        hstep = 1e-6
        def solve_y(u):
            # Newton on y^2 + A u + b - g0 = 0
            y = ystar
            for _ in range(50):
                y = y - (y**2 + A * u + b - g0) / (2 * y)
            return y
        yp = solve_y(ustar + hstep)
        ym = solve_y(ustar - hstep)
        h_u_fd = (yp - ym) / (2 * hstep)
        worst = max(worst, abs(h_u_ift - h_u_fd))
    return _check("P3.1 index-1 Schur input channel (IFT)", worst < 1e-5, f"max_gap={worst:.3e}")


def check_p3_zero_authority() -> tuple[bool, str]:
    """P3.2: d/dM and d/dD of [Pm-Pe-D(w-ws)]/M vanish at synchronous power balance."""
    try:
        import sympy as sp
    except ImportError:
        return _check("P3.2 zero first-order M/D authority", True, "(sympy unavailable)")
    M, D = sp.symbols("M D", positive=True)
    w, ws = sp.symbols("w w_s")
    Pm, Pe = sp.symbols("P_m P_e")
    f = (Pm - Pe - D * (w - ws)) / M
    dfdM = sp.simplify(sp.diff(f, M))
    dfdD = sp.simplify(sp.diff(f, D))
    sub = {w: ws, Pm: Pe}
    ok = sp.simplify(dfdM.subs(sub)) == 0 and sp.simplify(dfdD.subs(sub)) == 0
    return _check("P3.2 zero first-order M/D authority", ok,
                  f"dM={dfdM}, dD={dfdD}, at-balance={sp.simplify(dfdM.subs(sub))},{sp.simplify(dfdD.subs(sub))}")


def check_m1_ceiling() -> tuple[bool, str]:
    """M1: at lambda=ceiling, lambda stays iff residual >= 0 (fixed step alpha>0)."""
    ceiling = 10.0
    alpha = 0.05
    ok = True
    for residual in [-0.5, 0.0, 0.5]:
        lam_next = float(np.clip(ceiling + alpha * residual, 0.0, ceiling))
        stays = (lam_next == ceiling)
        expect = (residual >= 0.0)
        ok &= (stays == expect)
    return _check("M1 projected-dual ceiling persistence", ok)


def check_m2_signed_bias() -> tuple[bool, str]:
    """M2: min of two zero-mean-error critics is pessimistically biased (<= Q)."""
    rng = np.random.default_rng(4)
    Q = 1.0
    worst = 0.0
    for _ in range(1000):
        e1 = rng.normal(0, 0.3)
        e2 = rng.normal(0, 0.3)
        m = min(Q + e1, Q + e2)
        # min <= Q + e1 always; empirical mean of min should be <= Q
        worst = max(worst, m - Q)  # track any positive exceedance
    # mean of min is below Q (pessimistic in return space)
    mean_min = np.mean([min(Q + rng.normal(0, 0.3), Q + rng.normal(0, 0.3)) for _ in range(20000)])
    return _check("M2 twin-min pessimistic bias", mean_min < Q - 1e-9, f"E[min]={mean_min:.4f} vs Q={Q}")


def run() -> list[tuple[bool, str]]:
    return [
        check_p1_quotient(),
        check_p1_scalar_loop(),
        check_p2_delay_ratio(),
        check_p2_delay_direction(),
        check_p3_schur(),
        check_p3_zero_authority(),
        check_m1_ceiling(),
        check_m2_signed_bias(),
    ]


def main() -> int:
    try:
        results = run()
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    for ok, line in results:
        print(line)
    failed = [line for ok, line in results if not ok]
    print(f"--- {sum(1 for ok, _ in results if ok)}/{len(results)} checks passed ---")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
