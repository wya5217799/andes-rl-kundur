# Theory-audit bundle import note

## Scope

- Source: `C:\Users\27443\Downloads\vsg_theory_audit_bundle\vsg_audit_bundle`
- Imported for the fixed-title ICEMS 2026 manuscript:
  `Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning`.
- Role: advisory mathematical review and reproducibility support only.
- It is not an experiment feed, a registered claim, a new VSG simulation, or a controller-class infeasibility certificate for the project plant.

## Integrity checks performed on 2026-08-16

1. All 26 source files matched the supplied `MANIFEST.sha256`.
2. `vsg_audit_verify.py`, `symbolic_exact_checks.py`, the synthetic LP certificate, and the conic Farkas verifier were rerun in a fresh temporary directory without installing new dependencies.
3. Exact symbolic and certificate outputs reproduced. Numerical outputs agreed semantically; byte differences were limited to platform-dependent line endings and last-bit floating-point formatting.
4. The imported report was reviewed against the active manuscript, same-line reports, and the project evidence boundary.

## Audit decision

**CONDITIONAL PASS as advisory theory.** The package strengthens the reduced-model reasoning but does not raise the empirical claim ceiling.

Safe to use:

- Under diagonal nonsingular $M,D$ and a coupling matrix that preserves the common/differential subspaces, exact rational separation is equivalent to homogeneous $M=mI,D=dI$. Either complete cross-block identity alone is sufficient under the stated coupling assumptions.
- For zero-state multiplicative parameter feedback, the policy slope does not enter the local plant-state Jacobian through the coefficient-modulation path.
- Under a locally Lipschitz, same-bias, common-active-mode model, the controller-to-controller state difference is bounded by $O(\varepsilon^2)$ on a fixed horizon; the antisymmetric component need not be cubic.
- For an index-1 DAE, algebraic elimination gives $A_r=f_x-f_yg_y^{-1}g_x$ and $B_{u,r}=f_u-f_yg_y^{-1}g_u$. A nonzero $B_{u,r}$ can restore additive first-order authority, so the ODE multiplicative lemma cannot be transferred to the project DAE without calculating the actual Jacobians.
- A Youla/SLS infeasibility statement is legitimate only for a precisely bounded stable convex class with an independently verified dual lower bound or Farkas certificate.

Not safe to use as a manuscript result:

- the synthetic signed-probe curves, numerical counterexamples, or certificate demonstrations as VSG experiment evidence;
- any claim that all causal, nonlinear, local, finite-order, or MARL controllers are infeasible;
- a cubic-leading signed-probe claim for the implemented asymmetric decoder;
- a claim that the energy-port controller succeeds because of an identified additive DAE channel;
- a claim that the actual ANDES DAE satisfies the imported Jacobian assumptions;
- a solver status or the included template as a certificate for the project plant.

## Remaining project-specific inputs

The theory can be strengthened only after obtaining the actual reduced or DAE Jacobians, measured input/output maps, algebraic conditioning, signed-amplitude trajectories with active-mode logs, or the exact affine Youla/SLS response matrices and conic dual certificate. None is inferred from this imported package.
