# Paper-ready bounded wording for U1–U9

These paragraphs are intentionally limited to the strength supported by the frozen objects and the assumptions stated in `01_complete_solution.md`.

## U1 — FIR-Youla/SLS certificate status

For the frozen linearized energy-port model, feasibility over a compact, strictly causal 10-tap differential Youla class can in principle be decided by a finite-horizon conic phase-I program once an exact doubly-coprime factorization, lifted response matrices, and the actuator active mode are exported. The current artifact package does not contain those certificate-bearing arrays; therefore it supports neither a feasible witness nor an infeasibility certificate for that class. Any future certificate would remain local to the declared model, profile bank, horizon, coefficient bound, and actuator mode.

## U2 — Message value and finite learning cost

A crossed actor-access, critic-access, and reward design with a marginal-preserving non-neighbour placebo separates semantic message effects from input-dimensionality effects at a fixed training budget. The resulting contrasts remain algorithm- and budget-specific. They identify the population value of information only if optimization gaps for the nested policy classes are independently controlled.

## U3 — Stateful slew projection

A stateful slew limiter makes the previous executed command part of the Markov state. A raw-command critic is valid only on this augmented state with the projection included in the transition kernel; an executed-command critic is equivalent after push-forward of the policy. Omitting the previous executed command aliases distinct transitions and makes a critic trained on raw commands Bellman-inconsistent.

## U4 — Training constraints versus physical guards

The episodic common-mode quadratic constraint is not an inner approximation of the registered trajectory-level guard set. It controls an expected normalized second moment, whereas the gate is a profile-wise intersection of reference-relative endpoint, peak, RoCoF, action-stress, saturation, and validity constraints. A finite-bank max-violation phase-I program is required to distinguish a guard-clean witness from optimizer failure in a named controller class.

## U5 — Complete M/D sensitivity

The sensitivity of the candidate-to-reference energy ratio contains equilibrium, plant input/output, discretization, controller, headroom, and reference-denominator terms. The previously reported state-matrix-only contributions are mixed and are not a coordinate-invariant causal attribution. A complete total derivative requires the exported sampled input/output model and a fixed actuator mode.

## U6 — Fractional delay

On the registered nonlinear bank, the differential-energy threshold of 0.95 is bracketed between zero and one 0.2-s sample delay, assuming continuity of the fractional-delay execution map. This is a finite-bank performance boundary. The available band-limited return-ratio data do not determine a pole-crossing, phase-margin, or robust-stability delay margin.

## U7 — Leading M/D authority

At the registered synchronous equilibrium, direct M/D commands have zero additive first-order reduced-state columns. Under a fixed smooth DAE mode and a zero-bias Lipschitz feedback law, their leading disturbance-dependent authority is bilinear, so the controlled-minus-zero-action response is second order in disturbance amplitude over a fixed local horizon. A quantitative comparison with additive power actuation requires the mixed derivative tensors and the additive port's lifted singular values.

## U8 — Approximate common/differential separation

Approximate common/differential separation is controlled jointly by projector commutators, input/output alignment, and resolvent conditioning. In the balanced swing reduction, M/D heterogeneity enters the off-diagonal dynamic-stiffness block explicitly, but it does not alone bound finite-window cross energy. Near resonances or algebraic singularities can amplify arbitrarily small asymmetry, while large heterogeneity can yield small cross energy under weakly responsive scaling or output projection.

## U9 — R458 interpretation

One schedule was selected from the frozen 350-member family using only two development profiles and was then evaluated once on four fixed evaluation profiles. A passing result is a guard-clean transfer witness for that schedule on the reported finite bank. Because the evaluation profiles are fixed rather than sampled from a declared population, the transfer count does not estimate a distributional success probability or support topology generalization.

## Prohibited upgrades

Do not convert any paragraph above into claims about all controllers, all MARL policies, arbitrary topologies, global nonlinear stability, safety, deployment readiness, or a population transfer probability. Do not call the R450 endpoint threshold a stability margin, the R450 scalar seam an uncertainty norm, R456 a KKT/infeasibility certificate, or a missing U1 certificate a negative certificate.
