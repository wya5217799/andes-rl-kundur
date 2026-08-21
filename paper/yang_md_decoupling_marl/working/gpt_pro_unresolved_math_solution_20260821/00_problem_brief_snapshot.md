# GPT Pro brief — unresolved mathematics after R457, with R458 still active

Date: 2026-08-21 (Asia/Shanghai)  
Manuscript line: `yang-md-decoupling-marl`  
Fixed title: *Decoupling-Oriented Coordination of Paralleled  VSGs With Multi-Agent Reinforcement Learning*

## 0. Task for GPT Pro

Solve or sharply delimit every open item U1--U9 below. This is a **delta brief**:
the earlier advisory tasks P1--P3 and M1--M5 have already been answered or
experimentally dispositioned to the bounded extent listed in Section 2. Do not
repeat the old answers as if the later evidence did not exist.

For every item, return all of the following:

1. the strongest valid theorem, certificate, counterexample, or identifiable
   estimand under explicit assumptions;
2. a derivation or proof, with all dimensions, units, signs, sampling and
   operating-point assumptions stated;
3. the exact repository fields/files used and any quantity that is still
   unavailable;
4. a machine-checkable algorithm or pseudocode, including numerical
   conditioning and verification tolerances;
5. the smallest falsifiable new computation/experiment, with observables that
   support and refute the proposed mechanism;
6. paper-safe wording and prohibited stronger wording;
7. a three-way classification: algebraic identity, mechanism prediction, or
   paper-grade proposition.

If the supplied evidence cannot identify a requested conclusion, prove why it
is underdetermined or give two data-generating mechanisms consistent with the
same supplied observables. Do not invent missing plant matrices, trajectories,
or uncertainty bounds.

## 1. Non-negotiable object and evidence boundaries

- **Object A (main negative comparison):** four independently executed agents
  command bounded local `delta_M_i, delta_D_i` on four GENCLS VSG proxies in a
  fixed-connectivity modified Kundur system. M/D modulation is multiplicative
  parameter actuation, not additive power injection.
- **Object B (constructive companion):** feasibility-native energy-port
  actuation with a low-order ring-edge bandpass controller. Object A and Object
  B use different actuators, references, estimators, windows and banks. Their
  ratios must never be pooled into one causal comparison.
- The physical endpoints are 60-Hz quantities; controller semantics are frozen
  on a 50-Hz model base. Preserve that distinction.
- Common-frequency restoration, relative synchronization and inter-area
  differential motion are different estimands.
- Outcome-seeing oracle selection is a finite-family diagnostic, never a causal
  or deployable controller.
- R451 is retained `CANARY-INVALID`; it produced zero valid training manifests.
  Its directional partial output is not evidence.
- R458 has only a prospective plan at package time: no capacity, rehearsal,
  seal, selection, evaluation, feed or claim exists. Do not predict its result.
- No successful-MARL, universal message-value, controller-class impossibility,
  stability, safety, topology-generalization or deployment claim is currently
  authorized.

Evidence precedence inside the package is: final formal guards and hashed
analysis -> current CLM claim cards -> same-round feed reports -> sealed result
files -> round verdict/plan -> manuscript and scratch notes.

## 2. What is already resolved or bounded (do not reopen without finding an error)

| item | latest bounded result | authoritative pointer |
|---|---|---|
| P3 first-order DAE authority | At the registered synchronous equilibrium, all eight reduced M/D command columns satisfy `B_{u,r}=f_u-f_y g_y^{-1}g_u=0` exactly. Leading authority is state-dependent/bilinear or higher order, not additive first-order force injection. | `results/research_loop/r446_md_authority_fd/formal_analysis.json`; `CLM-1390` |
| P1 A-channel sensitivity | For the nominal Object B small-signal model, candidate/reference contributions through `dA_d/d(log M)` and `dA_d/d(log D)` have opposite signs and similar magnitudes; both are `MIXED`, not candidate- or reference-dominant. | R449 analysis; `CLM-1400` |
| P2 integer delay curve | On one registered bank, differential-energy ratio is 0.9389468, 0.9502788 and 0.9893271 at delays 0, 1 and 2 samples. The exact small-signal MIMO pure-delay model predicts the normalized worsening within 10%. This is an endpoint boundary, not a stability margin. | R450 analysis; `CLM-1405` |
| M5 finite candidate grid | Corrected aggregation finds guard-clean joint headroom in `eval_b/c/d`, not `eval_a`; feasible candidate counts are 2, 6 and 1 for the passing profiles and 0 for `eval_a`. This is exhaustive only over the registered 350 candidates per profile. | R453 analysis; `CLM-1410` |
| M4 residual identity | Zero residual is a local maximum of both implemented regularized rewards on the registered four-direction/three-condition slice; this is objective-induced and not physical/global optimality. | R454 analysis; `CLM-1415` |
| M1 dual mechanics | The projected dual law is mechanically correct. Historical exploratory gaps can pin the cap, while final deterministic gaps release it. RMS constraint and saved value gradients materially conflict in 4/6 checkpoints. This is not a KKT or infeasibility certificate. | R456 analysis; `CLM-1420` |
| M2 critic-head hypothesis | A corrected output-preserving common-head intervention passes 0/5 causal chains in both information arms, while actors move materially. The specific common-head repair is refuted; universal critic irrelevance is not proved. | R457 analysis; `CLM-1425` |
| M3 message factorial | The intended 2x2x2 factorial plus shuffled placebo is invalid: the shift-by-two placebo preserves every semantic neighbour set, initialization preceded registered seeding, and reward changes were mixed with observation access. | R451 plan frontmatter + final algorithm audit |

## 3. Open mathematical problems

### U1 — Instantiate or refute the bounded FIR-Youla/SLS controller-class certificate

**Question.** For the frozen Object B reduced model, declared profile bank,
finite horizon, actuator/headroom map and a precisely bounded FIR controller
class, can a verified phase-I SOCP produce either (a) a feasible controller
witness satisfying all endpoint and guard constraints, or (b) a positive
dual/Farkas lower bound proving that exact class infeasible?

The procedural construction exists in
`tmp/yang_md_decoupling_marl/c1_youlas_sls_certificate.md`, but no project DCF,
SLS achievability map, lifted response matrix, primal solution or positive
dual certificate has been produced. Use the frozen R405 linearization matrices,
R447/R450 complex-response seam and R452/R453 guard data where valid.

Required subanswers:

- choose one certificate-bearing route (verified DCF/Youla or full output-
  feedback SLS), with exact dimensions and sign conventions;
- define the FIR order/coefficient set so the result is for a named bounded
  class, not all controllers;
- express finite-window differential/common endpoints and action RMS/TV/
  saturation constraints as affine/SOC constraints, or prove which are not
  convex under the frozen execution map;
- generate an independently checkable unscaled primal-dual certificate;
- state the nonlinear transfer condition: fixed active mode, exhaustive
  piecewise-affine modes, or a uniform remainder/IQC bound. Without one, keep
  the result local to the frozen linear class.

### U2 — A causally valid message-value / finite-learning-cost identification design

**Question.** Can the intrinsic value of neighbour information be separated
from finite-sample/optimization cost for the adapted-SAC family using nested
policy classes and a valid placebo, without changing reward and information in
the same contrast?

R410 and R431 have opposite cross-family message signs and are not causal
pairs. R438 is only observation-channel leaning. R451 was invalid before
training. Provide a replacement mathematical design, not a request to reuse
R451 outcomes.

Required subanswers:

- define population policy classes `Pi_X subseteq Pi_{X,N}` and the exact
  finite-budget estimands separately;
- construct a four-agent ring placebo that preserves declared marginals but
  **changes every agent's semantic neighbour pairing**; prove those two facts;
- orthogonalize actor access, critic access and reward terms so main effects
  and interactions are identifiable;
- specify paired/hierarchical uncertainty with training seed as the top-level
  unit and scenario trajectories below it;
- give support/refute observables for information value and finite-learning
  cost, including failure branches when optimization has not converged;
- state what remains non-identifiable even after the design.

### U3 — Correct Bellman semantics for a stateful slew projector

**Question.** The R431 lineage generated transitions with a stateful slew-
projected executed action but trained the critic on the raw pre-projection
action. Formulate the correct augmented MDP and quantify when the historical
Bellman target is inconsistent or biased.

Let raw policy output be `u_t`, previous executed action be `v_{t-1}`, and
executed action be `v_t=P(v_{t-1},u_t)` with amplitude/slew projection. Derive:

- the minimal Markov state (at least `(x_t,v_{t-1})`) and transition kernel;
- whether a critic should be `Q(z_t,u_t)` with deterministic `P` inside the
  environment, `Q(z_t,v_t)`, or a two-action representation, and the conditions
  under which these are equivalent;
- the correct replay tuple and target action semantics for SAC/TD3;
- an error/bias bound, aliasing counterexample, or non-identifiability result
  when raw `u_t` is stored while `(r_t,x_{t+1})` came from `v_t`;
- how entropy regularization changes when many raw actions map to the same
  executed action;
- a minimal one-step and multi-step numerical verification contract.

### U4 — Relate the training constraint set to the trajectory-level physical guard set

**Question.** Existing learners optimize expected discounted/episodic quadratic
surrogates, while the canary requires per-profile/per-seed reference-relative
IAE, peak, RoCoF, RMS, TV and saturation limits. Can any computable training
constraint guarantee inclusion in the registered guard set, or can a formal
counterexample show that the present surrogate cannot?

Required subanswers:

- write both feasible sets with consistent horizon, discounting, aggregation,
  reference normalization and units;
- prove sufficient conditions for set inclusion, or construct a smallest
  counterexample under the current definitions;
- propose the smallest aligned constrained objective (robust, chance-
  constrained, CVaR, distributionally robust, or exact finite-bank) and explain
  which guard components remain non-differentiable;
- integrate R456's observed RMS value/constraint gradient conflict without
  claiming it is universal;
- give a feasibility-before-training program that distinguishes no feasible
  policy in a named class from optimizer failure.

### U5 — Complete closed-loop M/D sensitivity beyond the A-channel approximation

**Question.** R449 differentiates only `A_d(rho)`. Derive the total sensitivity
of the finite-band response/energy ratio when `A_d,B_d,C_d,D_d`, equilibrium,
discretization, controller realization and headroom map may all depend on
`rho in {log M, log D}`.

Required subanswers:

- an exact derivative formula for the MIMO discrete closed-loop transfer and
  finite-band quadratic energy, including denominator/reference sensitivity;
- a numerically stable adjoint or Fréchet-derivative implementation;
- a decomposition whose terms are invariant enough to support a physical
  interpretation, or a proof that the requested attribution is coordinate-
  dependent;
- interval/error bounds for centered finite differences and the R405 reduced-
  model approximation;
- whether any gain-margin, phase-margin or unique failure-cause statement can
  follow from supplied data. If not, specify the missing loop quantity.

### U6 — Fractional delay and a formal local stability/robustness margin

**Question.** R450 supports an integer-sample endpoint-degradation curve but not
a pole-crossing or phase-margin result. Given the supplied MIMO command-break
loop, derive the strongest defensible fractional-delay statement.

Required subanswers:

- define a continuous/fractional delay operator consistent with `dt=0.2 s`
  and the sampled controller (not an undocumented Padé substitution);
- compute or bound the first destabilizing delay for the frozen linear model,
  with branch tracking for eigenvalue crossings;
- separate robust stability margin, nominal phase margin and the empirical
  nonlinear endpoint threshold;
- propagate the recorded 5.38% zero-delay seam discrepancy and small-signal
  approximation as uncertainty;
- state the minimum additional nonlinear delay points needed to localize the
  `r_d=0.95` endpoint crossing without turning it into a stability claim.

### U7 — Quantify second-order/bilinear M/D authority after the zero first-order result

**Question.** R446 proves zero additive first-order reduced-state authority at
the synchronous balance point. What is the leading nonzero local input-output
map of zero-bias M/D feedback during a disturbance, and how small is its
reachable effect relative to additive energy-port actuation?

Required subanswers:

- derive the second variation / Volterra kernel or bilinear realization caused
  by `1/M` and `-D/M` modulation, including the index-1 DAE reduction;
- identify conditions under which response differences scale as `O(epsilon^2)`
  and when nonsmooth active-mode changes break that scaling;
- give a finite-horizon bilinear reachability/energy bound under the registered
  amplitude and slew limits;
- propose a convergent finite-difference tensor probe and conditioning test;
- state whether a quantitative local disadvantage versus additive power input
  can be proved on the frozen model without claiming global impossibility.

### U8 — Approximate common/differential separation under heterogeneity and DAE/network asymmetry

**Question.** Manuscript Proposition 1 is an exact all-frequency theorem for a
balanced symmetric reduced model and homogeneous effective M/D. Derive a useful
quantitative bound for approximate finite-window separation, or prove that no
nontrivial bound follows from the currently declared quantities.

Possible ingredients are commutators with the common/differential projectors,
network imbalance, M/D heterogeneity, resolvent conditioning and output rank.
The result must cover only the object actually represented by its assumptions.

Required subanswers:

- an upper/lower bound for off-diagonal transfer or finite-window energy in
  terms of explicit heterogeneity/asymmetry measures;
- singular-frequency/repeated-mode conditions that make the bound vacuous;
- extension conditions from a reduced ODE to an index-1 DAE Schur complement;
- a counterexample if finite-window metrics admit arbitrarily small cross
  energy despite large parameter heterogeneity (or the converse);
- paper-safe wording that does not imply a universal Bode/product trade-off.

### U9 — Interpret R458's dev-selection/eval-transfer experiment without selection laundering

**Question.** R453 found profile-wise headroom by outcome-seeing evaluation
selection. R458 prospectively selects one of the same 350 schedules using only
`dev_a/dev_b`, then evaluates that one schedule once on `eval_a..d`. Before its
outcome exists, determine exactly what each possible branch can establish.

Required subanswers:

- verify the frozen lexicographic selection rule and identify any implicit
  multiple-comparison/selection effect remaining on development data;
- give a branch-by-branch interpretation for priority 1, priority 2 and
  fallback priority 3, combined with transfer counts 0--4;
- state the valid unit of analysis and what, if any, confidence/generalization
  bound is possible with only four fixed evaluation profiles;
- explain why success is a finite-bank transfer witness rather than arbitrary-
  controller, distributional or topology generalization;
- propose a future statistical design (additional independently frozen profile
  banks or distributional model) that could support a quantified transfer
  probability, without changing R458's frozen gate.

## 4. Items intentionally excluded from this line's math pack

- `Q-0112` is the repository's only formally open Question entity, but it was
  opened by the repository-global R445 residual-headroom intake and concerns
  exact R352/R353 observation histories on the model-first successor line. It
  appears in later plan snapshots but is **not** a Yang-line problem, so it is
  excluded here.
- Exact Yang-2023 SAC reproduction, extra training seeds, language polishing,
  page compression, citation verification, topology/HIL/EMT evaluation and
  venue compliance may be future work, but they are not unresolved mathematics
  by themselves.
- Retuning/retrying the failed R404 direct-M/D route or treating R399's finite
  oracle as a global optimum is prohibited.

## 5. Data map

The zip root contains `manifest.json` and `SHA256SUMS`. Major evidence groups:

- current manuscript line, all registered feeds, earlier GPT briefs/advisories:
  `paper/yang_md_decoupling_marl/`;
- frozen reduced-model matrices and Object B response data: R405, R447, R449,
  R450 result roots;
- Object A first-order authority: R446 result root;
- message contrast and invalid causal design: R410/R431/R438 summaries, R451
  plan/runner/tests and retained logs;
- finite-grid/Pareto and active transfer plan: R452/R453 results, R458 plan and
  runner;
- residual/dual/critic diagnostics: R454, R456 and R457 formal summaries and
  manifests;
- relevant source, runners, probes and tests: `src/andes_rl_kundur/` plus the
  selected R405/R446--R458 scripts and tests.

Large checkpoint tensors and raw replay buffers are intentionally omitted from
this upload-oriented package; their cryptographic inventory is retained in the
included formal manifests. The included machine-readable analyses contain the
decision-bearing numbers. If GPT Pro identifies a calculation that truly needs
one omitted tensor/trace, name the exact manifest path and field rather than
guessing.
