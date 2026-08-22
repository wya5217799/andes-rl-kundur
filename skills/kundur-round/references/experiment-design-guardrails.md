# Experiment design guardrails — 三包外部答案吸收后的实验设计护栏 (2026-08-22)

Source: three external answer packages absorbed 2026-08-22 (agent-results /
complete-outputs / deep-solutions, staged under
`tmp/yang_md_decoupling_marl/gpt_pro_math_*`). Every rule below was either
verified against repo code or replayed repo-side (records in
`tmp/yang_md_decoupling_marl/` intake trees + gate_calibration_log).

Use: before writing any NEW experiment plan (evidence or prospective
scratch), read this file; the plan's design section must follow the
applicable rule or register an explicit deviation with owner authorization.
The active-round plan (R472) stays frozen; these rules bind successors and
verdict wording, not the running execution.

## A. 信息/来源实验的干预纯度 (U2 lesson, code-verified)

1. Source interventions must be a same-time permutation of the authentic
   source pool (synchronous replica wiring), never an exogenous pre-recorded
   random-policy donor bank. The 2026-08-22 audit showed the current P source
   reads a random-action donor trajectory while N reads the contemporaneous
   controlled trajectory; `donor_marginal_audit` is donor-internal and never
   compared realized P vs N inputs.
2. Falsification-first: before training, run the routing-only check on the
   two replicas: sort(N over e,i) == sort(P over e,i) per
   slot/feature/scenario/time; every source tuple changed; no P donor is a
   true neighbour of its recipient; P/N read the same contemporaneous state
   pool before routing. Any failure = `FACTORIAL-INVALID`, no training.
3. Finite-budget contrasts decompose as `I* + (L_X,B - L_XN,B)`; without
   optimization-gap control the contrast is a total algorithm effect of
   authentic-neighbour vs exogenous-donor source, and must be worded as such.
   Seed = top-level inference unit; per-seed scenario aggregates before
   paired contrasts; n=6 bootstrap is unstable — prefer randomization
   inversion over the pair labels; materiality gate tests lower bound
   > log(1.10), not merely non-zero effect.

## B. Feasibility-before-training ladder (U4 lesson)

1. For any named finite / enumerable / convex controller class: exact
   enumeration or convex phase-I FIRST, before learning.
2. `t<=0` witness exists -> then learning is allowed (question = "can the
   optimizer find it?"). `t>0` with a rigorous lower bound -> the named class
   is infeasible; stop tuning within the class (change constraints,
   parameterization, or class — R463 already exhausted the 350-schedule
   class).
3. Neural training failure = optimization failure only; never a class
   infeasibility claim.
4. Expected/surrogate cost does NOT imply profile-wise physical guard
   inclusion (two independent counterexamples: rare bad profile under
   expectation; identical common trace with arbitrary action stress). Never
   write "budget implies no-harm".

## C. Certificate ladders (U1/U6/U7/U8 lessons)

1. Finite-class infeasibility: cone phase-I -> replayable primal/dual ->
   exact rational support certificate (Fraction arithmetic + integer sqrt
   upper bounds), replayed with sidecar hash checks. The QY10 certificate
   (t >= 0.0599381277975427... > 0) is the reference pattern.
2. Delay/stability: grid pole scans are grid results. Continuous-interval
   claims need interval eigenvalue enclosure / verified Lipschitz bound /
   adaptive crossing search. A performance-threshold crossing (r_d=0.95) is
   a continuity-qualified bracket, never a stability margin.
3. Second-order authority: `f_u(0)=0` does not exclude pure `u^2`.
   Bilinear-only claims need the family-invariance test
   (`f(0,q,0)=0, h(0,q,0)=0` over neighbouring q) or must retain the
   pure-q quadratic term. Nonsmooth controller/decoder at zero -> piecewise
   Volterra kernels, no smooth Taylor theorem.
4. Separation bounds: report asymmetry, resolvent/Schur conditioning, I/O
   rank and window together; a full-state commutator is computed only after
   a verified device-permutation representation, otherwise
   `NOT-COMPUTED-BY-DESIGN`.

## D. Transfer/probability claims (U9 lesson)

- k/4 fixed profiles = a finite-bank witness, never a probability. Any
  probability claim needs: declared profile/topology generator, frozen
  dev/test, one-time selection, m independent test profiles, profile as the
  Bernoulli unit, pre-registered exact binomial / Clopper-Pearson CI.

## E. Executed-action semantics (U3 lesson, R460-verified)

- Previous executed action is part of the Markov state; replay, current
  critic, target critic and actor objective all use projected executed
  actions; raw-policy entropy is labelled `raw_policy_entropy_regularizer`,
  never executed-action entropy.

## F. Next-round priorities (three chats agree)

- P0: message-value factorial successor built on Rule A design (synchronous
  replica placebo). R472 stays frozen; its verdict carries the Rule A.3
  wording boundary plus the seal-staleness note (formal_seal
  training_executed=false never updated — record at close-out).
- P1: U6 continuous-certificate ladder (Rule C.2); U7 family-invariance test
  (Rule C.3); stop U4-class tuning (Rule B.2).
- Recommended successor route (deep-solutions): compute
  `epsilon*(B_+, I_local/consensus)` — freeze the same 16 scenarios,
  bound max physical/robust epsilon for B_+ vs I_4; deterministic convex
  control on the common channel with the learned residual only on zero-sum
  edge channels; add a common scalar consensus signal only if aliasing is
  certified; train a neural residual only after physics / information /
  family / robust margins are all strictly positive.

## Provenance

- U2 code facts: `scripts/run_r470_u2_source_factorial.py::{source_rows,
  generate_donor_and_base, donor_marginal_audit}`.
- U1 exact certificate: `tmp/yang_md_decoupling_marl/gpt_pro_math_agent_results_20260822/
  verification/` (repo rerun PROVED).
- Priorities: agent-results README_AGENT_HANDOFF + deep-solutions MASTER_SOLUTION
  section 三.
