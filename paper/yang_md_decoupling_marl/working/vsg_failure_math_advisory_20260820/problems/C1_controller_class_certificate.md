# C1 — Controller-class certificate via FIR-Youla/SLS parameterization

**Type label: (P)**

## Headline result

A defensible controller-class no-headroom statement is possible, but only after the project replaces the demonstration search with an exact closed-loop response parameterization and an independently checkable conic certificate. The recommended route is a verified doubly-coprime/Youla parameterization around the frozen stable baseline, with a finite-impulse-response Youla variable constrained by explicit order, information structure, coefficient bounds, and well-posedness conditions. For fixed profiles and fixed positive baseline-energy denominators, the finite-window differential and off-diagonal outputs are affine in the FIR coefficients and the registered energy limits become second-order-cone constraints. A positive verified dual lower bound for a conic phase-I problem then proves infeasibility only for that named class, model, profile bank, horizon, and execution map. The shipped solver is explicitly a blueprint rather than such a certificate [C1-S01], and the imported audit permits only this bounded class-level conclusion [C1-S02].

## Hard facts

The package's demonstration solver records `"formal_dual_certificate": False` [C1-S01]. The theory-audit import note states that a Youla/SLS infeasibility claim is legitimate only for a precisely bounded stable convex class with an independently verified dual lower bound or Farkas certificate [C1-S02]. No project-specific doubly-coprime factorization, exact affine response matrices, internal-stability verification, nonlinear-remainder bound, primal-dual conic solution, or independently checked dual certificate is shipped. Consequently, the package presently supports a rigorous program specification, not a controller-class infeasibility result.

## Evidence binding

- `[C1-S01]` is package-source evidence at `tmp/yang_md_decoupling_marl/vsg_v2_fir_response_solver.py`, line `L269`, for the field-like key `formal_dual_certificate` with shipped value `False`. This is a source-code status flag, not a sealed JSON performance number.
- `[C1-S02]` is package-source evidence at `paper/yang_md_decoupling_marl/working/theory_audit_bundle/IMPORT_NOTE.md`, the `Safe-to-use` bullet requiring a precisely bounded stable convex class and an independently verified dual lower bound or Farkas certificate.
- No project-specific numerical certificate value is used in C1. The horizon $H$, coefficient bound $\beta$, profile set $\mathcal S$, response tolerances, phase-I slack bound, dual lower bound $\delta$, and nonlinear discrepancy allowance $\varepsilon$ are symbolic and **HYPOTHETICAL until the project seals them**. `verification/examples/HYPOTHETICAL_c1_dual_example.json` is only a rational-arithmetic checker smoke test and is not evidence about the project plant.

## Assumption set

The proposition below is conditional on the following project-supplied objects. Symbols such as the FIR horizon $H$, coefficient bound $\beta$, profile set $\mathcal S$, and robustness radii $\varepsilon_s$ are **design variables or HYPOTHETICAL quantities until sealed by the project**; no numerical values are assigned here.

1. **Frozen discrete-time generalized plant.** A gauge-fixed, sampled local model is supplied in the form
   $$
   x_{k+1}=Ax_k+B_1w_k+B_2u_k,
   \qquad
   z_k=C_1x_k+D_{11}w_k+D_{12}u_k,
   \qquad
   y_k=C_2x_k+D_{21}w_k,
   $$
   with a declared sample period, input/output ordering, operating point, active limiter/headroom mode, and discretization method. Algebraic feedthrough is such that the feedback interconnection below is well posed.
2. **Verified stable baseline.** A proper controller $K_0$ internally stabilizes the frozen plant. Either a normalized or ordinary doubly-coprime factorization over $\mathcal{RH}_\infty$ is supplied and its Bézout identities are numerically and symbolically checked, or an equivalent lower-LFT generator $J$ is supplied and independently verified to parameterize all internally stabilizing perturbations around $K_0$ in the declared convention.
3. **Bounded convex Youla class.** The search variable is
   $$
   Q(z)=\sum_{h=0}^{H-1}Q_hz^{-h},
   $$
   with coefficient vector $q=\operatorname{vec}(Q_0,\ldots,Q_{H-1})$. The class $\mathcal Q$ imposes explicit affine sparsity/locality constraints, any required strict-causality constraints, and a compact convex coefficient bound such as $\lVert W_q q\rVert_2\le\beta$ or componentwise bounds. The chosen direct term guarantees well posedness for every $q\in\mathcal Q$.
4. **Fixed finite-window experiment map.** For every sealed profile $s\in\mathcal S$, the initial condition, disturbance/probe sequence, output projection, window, quadrature weights, and positive local-reference energies $E_{d,0,s}$ and $E_{\times,0,s}$ are fixed independently of $q$.
5. **Convex guard representation.** Action, slew, and any linearized physical no-harm restrictions are represented as affine equalities/inequalities or second-order-cone constraints in $q$. Any nonconvex guard is excluded from the certified class unless replaced by a proved convex sufficient condition.
6. **Conic regularity.** The phase-I SOCP described below is feasible for sufficiently large relaxation $t$, has a finite optimum, and satisfies relative Slater regularity after equality constraints are eliminated or treated on their affine hull. The data used by the independent verifier are identical to the data used by the solver.
7. **Nonlinear transfer, when claimed.** A claim about the implemented nonlinear headroom/DAE map additionally requires either one fixed affine active mode on a verified forward-invariant tube or a uniform finite-window discrepancy bound between the nonlinear and linear response maps. Without one of these, the certificate is local to the frozen linear model.

## Proposition C1.1 — internally stable affine Youla response class

Let $P_{22}$ denote the transfer matrix from $u$ to $y$ of the frozen generalized plant. Under Assumptions 1–3, construct a verified lower-LFT generator $J$ from a doubly-coprime factorization associated with $K_0$. Then

$$
K(Q)=\mathcal F_\ell(J,Q),\qquad Q\in\mathcal Q\subset\mathcal{RH}_\infty,
$$

is internally stabilizing and finite order for every admissible FIR $Q$. Moreover, every closed-loop transfer from $w$ to a declared performance output $z$ has the affine form

$$
T_{zw}(Q)=T_{11}+T_{12}QT_{21},
$$

where $T_{11},T_{12},T_{21}\in\mathcal{RH}_\infty$ are fixed by the plant, baseline, and factorization convention.

### Proof sketch

The Youla-Kučera theorem states that, after a valid doubly-coprime factorization and its Bézout identities are fixed, the lower LFT $\mathcal F_\ell(J,Q)$ maps every stable proper $Q$ satisfying the stated well-posedness convention to an internally stabilizing controller. An FIR transfer is stable and finite dimensional. Standard lower-LFT algebra then gives the model-matching map $T_{zw}=T_{11}+T_{12}QT_{21}$, which is affine in $Q$. The proof applies only to the exact verified factorization and sign convention; substituting an unverified formula or merely stabilizing a nominal simulation does not establish the premise.

### Equivalent SLS route

If the project prefers system-level synthesis and the required state is available, it may instead search stable closed-loop responses $\Phi_x,\Phi_u$ satisfying

$$
(zI-A)\Phi_x-B_2\Phi_u=I,
\qquad
\Phi_x,\Phi_u\in z^{-1}\mathcal{RH}_\infty.
$$

Exact FIR truncation must include the terminal coefficient closure implied by this affine identity. For output feedback, the full output-feedback SLS response matrix and both affine achievability identities must be enforced; omitting either identity is not a valid parameterization. If only approximate FIR achievability is imposed, the residual operator $\Delta$ must be bounded with a proved condition such as $\lVert\Delta\rVert<1$, and all performance bounds must be inflated through the corresponding robust-stability factor. This SLS alternative supplies the same type of affine response coordinates but is not interchangeable with an unconstrained FIR input-output fit.

## Proposition C1.2 — finite-window energy constraints are conic

Under Assumptions 1–5, stack the weighted finite-window differential and off-diagonal samples for profile $s$. There exist project-computed matrices and vectors

$$
y_{d,s}(q)=b_{d,s}+A_{d,s}q,
\qquad
y_{\times,s}(q)=b_{\times,s}+A_{\times,s}q.
$$

For fixed positive denominators, the target requirements

$$
\frac{\lVert y_{d,s}(q)\rVert_2^2}{E_{d,0,s}}\le \tau_d,
\qquad
\frac{\lVert y_{\times,s}(q)\rVert_2^2}{E_{\times,0,s}}\le \tau_\times
$$

are exactly equivalent to the second-order-cone constraints

$$
\lVert b_{d,s}+A_{d,s}q\rVert_2
\le\sqrt{\tau_dE_{d,0,s}},
$$

$$
\lVert b_{\times,s}+A_{\times,s}q\rVert_2
\le\sqrt{\tau_\times E_{\times,0,s}}.
$$

The feasible set obtained by intersecting these constraints over $s\in\mathcal S$ with $\mathcal Q$ and the convex guard constraints is closed and convex; it is compact when $\mathcal Q$ is compact.

### Proof

By Proposition C1.1, the closed-loop transfer is affine in $Q$, and an FIR $Q$ is affine in its coefficient vector $q$. Convolution with each fixed finite disturbance/probe trajectory, followed by fixed output selection and fixed quadrature weighting, is linear. Therefore each stacked trajectory is affine in $q$. Squaring the Euclidean norm yields the finite-window weighted energy. Because the denominator is fixed and positive, taking the positive square root gives an equivalent Lorentz-cone inequality. Intersections of affine sets, second-order cones, and a convex class remain convex; compactness follows from the explicit coefficient bound.

### Limitation on ratio denominators

If the local-reference energy, normalization, initial condition, active headroom mode, or experiment trajectory changes with $q$, then the ratio is generally not represented by the preceding SOC. It must be frozen by protocol, lifted into a separately proved convex representation, or treated as a nonlinear robust constraint. It may not be silently absorbed into $A$ or $b$.

## Proposition C1.3 — class-limited infeasibility from a verified dual lower bound

For each conic constraint, let $c_i>0$ denote its target radius and let $A_iq+b_i$ denote its affine response. Form a common-slack phase-I SOCP

$$
\begin{aligned}
 t_\star=\min_{q,t}\quad & t\\
 \text{s.t.}\quad
 & \lVert A_iq+b_i\rVert_2\le c_i+t, && i\in\mathcal I_E,\\
 & a_j^\top q-b_j\le t, && j\in\mathcal I_A,\\
 & q\in\mathcal Q,\\
 & t\ge \underline t,
\end{aligned}
$$

where $\underline t$ is any declared finite lower bound that does not remove a target-feasible point. Under Assumption 6:

1. the original target system is feasible if and only if $t_\star\le0$;
2. strong conic duality holds and the primal and dual optima coincide;
3. any independently verified dual-feasible point with objective value $\delta>0$ proves that no controller in the exact class $\{K(Q):Q\in\mathcal Q\}$ satisfies all certified targets and guards on every profile in $\mathcal S$.

### Proof sketch

A point satisfying the original constraints is feasible in phase I with $t=0$, so it implies $t_\star\le0$. Conversely, if $t_\star\le0$, every right-hand side is no smaller at $t=0$ than at the optimal nonpositive $t$, so the same $q$ satisfies the original system. The phase-I problem is an SOCP with affine equalities and a compact convex coefficient set. Relative Slater regularity gives strong duality and attainment. Weak duality says every dual-feasible objective is a lower bound on $t_\star$; therefore a verified lower bound $\delta>0$ implies $t_\star>0$ and excludes every member of the named class. This proves neither infeasibility outside $\mathcal Q$ nor impossibility for nonlinear, time-varying, unbounded-order, or differently informed controllers.

## Corollary C1.4 — when a finite-family oracle is a certificate

A finite-family evaluation becomes an exact certificate only for the class

$$
\mathcal K_{\mathrm{finite}}=\{K_1,\ldots,K_N\}
$$

when all of the following are sealed:

1. the class definition lists every member and contains no continuous unsampled parameter, hidden schedule, adaptive state, or stochastic policy realization;
2. the evaluation profile bank, initial states, disturbances, numerical solver, tolerances, guard rules, and reference denominators are fixed;
3. every $K_i$ is evaluated on every required profile with no unresolved simulation or logging failure;
4. deterministic outputs are reproduced from immutable inputs, or all allowed random outcomes are exhaustively included in the class;
5. for each $K_i$, at least one required target or guard is mechanically shown to fail.

Under those conditions, exhaustive enumeration proves only

> no member of $\mathcal K_{\mathrm{finite}}$ passes the frozen test protocol.

A grid search is not a certificate for the continuous family containing the grid, and retaining only a winner is not a certificate even for the generated finite set unless all candidate outcomes are recoverable and checked.

### Proof

The statement follows by finite universal quantification: the class is exactly the enumerated list, and every element has a verified failing predicate. If the list is only a sample from a larger class or any outcome is absent, the universal quantifier is not established.

## Proposition C1.5 — transfer to the nonlinear headroom map

Define the linear phase-I violation function

$$
v_{\mathrm{lin}}(q)=\max\!\left
\{\lVert A_iq+b_i\rVert_2-c_i\}_{i\in\mathcal I_E},
\{a_j^\top q-b_j\}_{j\in\mathcal I_A}
\right),
$$

and let $v_{\mathrm{nl}}(q)$ be the corresponding violation computed from the implemented nonlinear DAE and headroom map on the same finite window. Suppose the project verifies the uniform discrepancy bound

$$
\sup_{q\in\mathcal Q}|v_{\mathrm{nl}}(q)-v_{\mathrm{lin}}(q)|\le\varepsilon
$$

on a forward-invariant tube and a fixed active mode. If the independently certified linear lower bound satisfies $\delta>\varepsilon$, then

$$
\inf_{q\in\mathcal Q}v_{\mathrm{nl}}(q)\ge\delta-\varepsilon>0,
$$

so the same class is infeasible for the nonlinear protocol within that tube. Conversely, a linearly feasible controller transfers as a nonlinear feasible controller only if its certified margin to every constraint exceeds the corresponding nonlinear response-error bound.

### Proof

For every $q$, $v_{\mathrm{nl}}(q)\ge v_{\mathrm{lin}}(q)-\varepsilon$. Taking the infimum and using the verified lower bound $\inf_qv_{\mathrm{lin}}(q)\ge\delta$ yields the result. The feasibility statement follows from the triangle inequality applied to each constrained response.

### Active-mode limitation

When saturation, projection, SOC/headroom limits, deadbands, or limiters switch mode inside the certified tube, a single affine map $b+Aq$ is generally invalid. The project must then use one of the following, with the choice named in the claim:

- exhaustive mode enumeration with exact mixed-integer/conic encoding for a finite piecewise-affine map;
- a robust outer approximation with a proved uniform remainder bound;
- an integral-quadratic/Lipschitz uncertainty description and robust synthesis/certification;
- a strictly local certificate restricted to one verified active mode and operating tube.

Absent one of these, the linear certificate must not be presented as a statement about the implemented nonlinear headroom map.

## Dual certificate computation recipe

The project can execute the following auditable sequence.

1. **Freeze the model and convention.** Export the gauge-fixed discrete generalized plant, sample period, signal ordering, baseline controller, and a DCF/LFT or exact SLS parameterization. Store all arrays in a canonical machine-readable format with hashes.
2. **Verify internal-stability algebra.** Check all Bézout or SLS achievability identities at coefficient level and over a dense frequency grid. The grid check is diagnostic; the coefficient-level identity is the certificate-bearing check. Verify baseline closed-loop poles and well posedness.
3. **Define the class exactly.** Seal $H$, FIR timing convention, sparsity/locality mask, direct-term rule, norm/box bounds, and any structural equalities. Record the dimension and an explicit map from $q$ to controller realization.
4. **Build response matrices independently.** For every profile, generate $A_{d,s},b_{d,s},A_{\times,s},b_{\times,s}$ by exact convolution or state lifting. Cross-check selected columns by symmetric finite differences of the frozen linear simulator.
5. **Build the conic phase-I problem.** Include all endpoint and convex guard constraints. Eliminate exact equalities or retain them explicitly. Apply only documented scaling transformations and save both scaled and unscaled data.
6. **Solve primal and dual.** Use a conic solver that exposes dual variables. Run at least one independent solver or independent arithmetic implementation. Solver status is diagnostic, not the certificate.
7. **Export a certificate bundle.** Save primal variables, dual variables, cone partition, objective values, scaling maps, and solver-independent residual definitions.
8. **Verify independently.** Recompute primal feasibility, dual feasibility, equality residuals, Lorentz-cone membership, complementary products, and the dual objective from the exported unscaled data. Use higher precision or directed interval/rational bounds to prove that the dual lower bound remains positive after all numerical residual allowances.
9. **Realize and recheck the controller.** Form $K(Q)$, verify properness, finite order, well posedness, and internal stability independently; compare its lifted response against direct linear simulation.
10. **Transfer or limit the claim.** Either prove the nonlinear discrepancy/active-mode condition in Proposition C1.5 and report the remaining positive margin, or state explicitly that the certificate applies only to the frozen linear class.

## Independent verification checklist

A certificate is acceptable only if the verifier can answer all of the following from shipped artifacts:

- Do the DCF Bézout or SLS achievability identities hold in the declared polynomial/rational convention?
- Is every allowed $Q$ stable, proper, finite order, structurally admissible, bounded, and well posed?
- Are the response matrices generated from the same frozen model, profiles, windows, quadrature weights, and fixed positive denominators used by the claim?
- Are all target and no-harm constraints represented exactly or by a named conservative relaxation?
- Is the phase-I primal value bounded, and does relative Slater regularity hold or is another strong-duality theorem cited and checked?
- Is the exported dual point inside every dual cone after undoing solver scaling?
- Do the dual equality residual and objective recompute independently to a certified lower bound strictly above zero?
- Is the positive lower bound larger than numerical error and, for a nonlinear claim, larger than the proved nonlinear discrepancy allowance?
- Does direct realization of $K(Q)$ preserve internal stability and reproduce the affine predicted response?
- Is the final sentence limited to the exact class, model, profile bank, horizon, information structure, and active-mode/robustness assumptions?

## Missing quantities and minimal experiments

The current package cannot instantiate the proposition because it lacks:

1. the frozen gauge-fixed linearized DAE or reduced discrete state-space matrices and declared sample period;
2. a verified stable-baseline DCF/LFT generator or exact SLS response parameterization;
3. the sealed FIR class definition: horizon, timing convention, locality mask, coefficient bounds, and well-posedness rule;
4. the exact affine response matrices for every endpoint and guard;
5. an unscaled primal-dual SOCP solution and independently verified positive dual bound;
6. a fixed-active-mode certificate or uniform nonlinear discrepancy bound for the state-dependent headroom map.

The minimal supplying experiment is not a new learning run. It is a registered linearization-and-lifting run at the frozen operating point: export the DAE Jacobians and active-mode log, discretize once with the declared method, verify a stable baseline and DCF/SLS identities, generate finite-window response columns by impulse lifting and finite-difference cross-checks, solve the conic phase-I program, and export the complete primal-dual certificate. A second minimal nonlinear validation then applies the realized candidate and symmetric coefficient perturbations inside the claimed operating tube to bound the linear/nonlinear response discrepancy and detect active-mode changes.

## Interpretation

The rigorous conclusion available now is procedural: the project has a mathematically valid route to a class-limited certificate, but no such certificate has yet been produced. A future positive dual bound would establish infeasibility only inside the explicitly frozen FIR-Youla/SLS class. It would not support statements about all stabilizing controllers, all finite-order controllers, all MARL policies, or the full nonlinear DAE unless the additional transfer conditions are verified.
