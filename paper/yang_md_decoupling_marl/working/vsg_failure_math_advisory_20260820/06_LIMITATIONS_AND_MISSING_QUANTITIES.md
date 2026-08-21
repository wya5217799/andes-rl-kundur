# Limitations, missing quantities, and minimum supplying experiments

This file collects the unsupplied quantities that prevent stronger claims. Any numerical design proposed below remains HYPOTHETICAL until registered and sealed.

## P1

The package lacks: (i) matched-block complex $G_K$ and $G_L$; (ii) a loop-broken complex $L$; (iii) matched finite differences in $M$ and $D$; and (iv) uncertainty estimates. The minimal experiment is a matched nominal/relaxed/stiff small-amplitude signed-probe sweep with complex response estimation for both the candidate and local reference. Without it, a margin-level causal explanation is not solvable from the shipped data.

## P2

The missing quantities are the same-bank $n=0$ endpoint, the exact sample period, the complex nominal loop $L_0$, the output numerator/weighting map, and uncertainty across repeated runs. The minimal experiment is a registered integer-delay sweep including zero delay, accompanied by one complex loop-identification export. Without those quantities, the package supports an exact symbolic delay law and two bounded failure observations, but no numerical analytic delay margin.

## P3

The package lacks the equilibrium residual vectors, $f_x,f_y,f_u,g_x,g_y,g_u$, algebraic conditioning, action-map derivative, active-mode log, and signed-probe trajectories with calibrated inputs. The minimal authority experiment is the equilibrium re-solve/centered-difference procedure above. The minimal identifiability experiment is a persistently exciting signed-probe record containing synchronized $w$, $\theta$, $\omega$, $\dot\omega$, operating-point metadata, and active-mode status, followed by constrained identification with held-out prediction.

## M3

Missing quantities are paired uncertainty for the R438 side assignment, actor-versus-critic message access, channel-specific critic gradients, representation conditioning, and a shuffled-message placebo. The minimal data addition is the registered factorial above with per-seed/per-profile endpoint records and gradient diagnostics. Until then, M3 remains a falsifiable mechanism prediction with medium confidence, not a theorem about the two algorithm families.

## M5

Missing quantities are action stress for non-winning schedules, candidate-level guard results, an identified local $G_{zu}$, and uncertainty/repeatability. The minimal data addition is the complete all-candidate R441-style table. Until that table exists, “no lower-stress winner exists” and “endpoint improvement necessarily costs the observed action increase” are unsupported.

## M4

The missing quantities are the true-return directional derivatives, curvature, critic action gradients, actor update vector, entropy/covariance contribution, and action-projection Jacobian. The minimal addition is the symmetric local perturbation plus checkpoint-gradient audit above. Without it, the exact identity-optimality condition is known mathematically, but its premises are not verified for R436.

## M1

Missing quantities are the full time alignment between residual and multiplier updates, actor/constraint gradients, cap/step interventions, per-profile residuals, and an independent feasible-policy witness. The minimal addition is an update-level trace with one cap sweep and one step sweep. Until then, the ceiling mechanism is high-confidence at the update level but the deeper primal cause remains unclassified.

## M2

Missing quantities are per-channel critic outputs and action gradients, aligned target statistics, true local return gradients, intervention-matched common outcomes, and temporal precedence. The minimal addition is the head-specific stabilization/frozen-replay audit. Until then, critic divergence is a plausible co-factor with medium-to-low causal confidence, not an identified driver.

## C1

The current package cannot instantiate the proposition because it lacks:

1. the frozen gauge-fixed linearized DAE or reduced discrete state-space matrices and declared sample period;
2. a verified stable-baseline DCF/LFT generator or exact SLS response parameterization;
3. the sealed FIR class definition: horizon, timing convention, locality mask, coefficient bounds, and well-posedness rule;
4. the exact affine response matrices for every endpoint and guard;
5. an unscaled primal-dual SOCP solution and independently verified positive dual bound;
6. a fixed-active-mode certificate or uniform nonlinear discrepancy bound for the state-dependent headroom map.

The minimal supplying experiment is not a new learning run. It is a registered linearization-and-lifting run at the frozen operating point: export the DAE Jacobians and active-mode log, discretize once with the declared method, verify a stable baseline and DCF/SLS identities, generate finite-window response columns by impulse lifting and finite-difference cross-checks, solve the conic phase-I program, and export the complete primal-dual certificate. A second minimal nonlinear validation then applies the realized candidate and symmetric coefficient perturbations inside the claimed operating tube to bound the linear/nonlinear response discrepancy and detect active-mode changes.
