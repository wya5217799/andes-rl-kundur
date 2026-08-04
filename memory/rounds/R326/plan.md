---
round: R326
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R326 plan - prospective constrained-QP solver adequacy repair

## TL;DR

Answer Q-0080 with one solver-only repair. Preserve the R325 model,
information, delay, horizon, objective, action map, physical limits, case
banks, comparison, estimands, gates, and stopping tree. Replace only the
sealed SLSQP numerical implementation with one pinned sparse convex-QP
implementation. Do not access the conditional holdout until convexity,
successful-prefix agreement, complete development execution, residual, and
deterministic replay gates all pass.

## Scientific acceptance criterion

- The action Hessian must be strictly positive definite for every frozen
  design, establishing one unique action optimum; no class-level mathematical
  feasibility claim is allowed.
- On every sample completed by a prospectively replayed R325 SLSQP prefix,
  candidate node and coordinate action plans must agree within `2e-5`
  absolute error and predicted outputs within `1e-6`. The action tolerance is
  the pre-existing scratch regression bound; the output tolerance is the
  repository regression convention. The auxiliary absolute-action variables
  and their conservative SOC envelopes are not equivalence objects because
  the strictly convex objective identifies the action optimum but does not
  make those slack variables unique. Candidate physical SOC limits remain a
  separate explicit hard gate.
- Both arms must complete all 32 unchanged development cases with zero solver
  failures, execution errors, explicit physical-constraint violations, or
  non-finite values. Maximum explicit physical-constraint residual must be at
  most `1e-8`. Raw primal and dual residuals must be reported, and each must be
  no larger than its independently recomputed OSQP absolute-plus-relative
  stopping tolerance.
- A second full development execution must be byte-identical after removing
  only the declared creation timestamp. Failure of any gate keeps the R325
  holdout inaccessible and closes the repair negative.

## Methodology

### Frozen implementation contract

- Reusable public seam: one solver object receives a frozen design, corrected
  estimate, previous node action, and SOC, then returns the existing
  `ConstrainedActionSolution` plus solver residual diagnostics.
- Formal execution seam: one thin round adapter prepares a seal, executes
  ordered case tasks with parent-only result writes, and performs deterministic
  analysis. Conclusion-affecting prefix matching and admission logic live in a
  round probe, not the adapter.
- Dependency: `osqp==1.1.3`; the seal records OSQP, NumPy, SciPy, Python,
  algebra backend, package metadata, and relevant source/binary hashes.
- Fixed settings: builtin direct linear solver, `max_iter=20000`,
  `eps_abs=1e-9`, `eps_rel=1e-9`, `polishing=False`,
  `warm_starting=True`, `adaptive_rho=True`,
  `adaptive_rho_interval=25`, `scaled_termination=False`, and
  `check_termination=25`. Only exact `solved` status is admissible.
- Pre-seal clarification after the first red-green slice: raw primal and dual
  residuals are scale-dependent under OSQP's documented stopping equations.
  Their gates therefore use residual divided by the independently recomputed
  absolute-plus-relative tolerance, with a maximum ratio of one. This replaces
  the initial raw `1e-8` gate before any seal or formal development execution;
  the explicit physical-constraint gate remains `1e-8`.
- Pre-seal clarification after the same-input canary: compare only the unique
  node/coordinate action plans and their predicted outputs. Do not compare
  non-unique auxiliary absolute-action or conservative SOC-envelope values.
  Freeze the already-existing scratch action bound `2e-5` and the independent
  output bound `1e-6`; no formal development or holdout result was accessed.
- Each case owns a fresh workspace; steps within one case may reuse its
  workspace. Formal case order is fixed, native numerical threads are limited
  to one per worker, workers write nothing, and the parent restores canonical
  order before serialization. Development uses at most eight workers; the
  faster candidate and any conditional holdout use at most four.
- The old solver is replayed only on development cases and stops each prefix at
  its first registered failure. Its trace is an equivalence reference, not a
  performance baseline and not a repair of R325.

## Comparison-identifiability gate

Decision: ALLOW for two bounded estimands.

- Numerical comparison: both implementations receive the same mathematical
  program, model state, information, action coordinates, feasible set, timing,
  objective, limits, and cases. Only the optimizer implementation and its
  numerical settings differ. The identified estimand is numerical agreement
  on successful old prefixes plus completion and residual adequacy on the
  development bank. Stay out: optimizer-family superiority, mathematical
  feasibility of every instance, controller efficacy, and runtime portability.
- Controller arms: both retain the R325 full executed plant, delivered
  information, four-coordinate action, node map, limits, observer template,
  normalization, horizon, objective, solver, case banks, metrics, and zero
  tuning budget. Synthesis retains versus deletes only the named cross blocks.
  If and only if both arms remain valid, the identified estimand is the value
  of those blocks in this fixed controller. Stay out: general decoupling value,
  distributed execution, agent value, learning, topology generalization,
  physical stability, safety, and title support.

## Red-green implementation order

1. Add one fast public-seam regression that reproduces the old solver
   termination on a frozen short development prefix and fails because no
   durable specialized solver exists.
2. Add the smallest solver implementation needed to pass one successful-prefix
   agreement and residual test; install and pin the dependency only after the
   red state is observed.
3. Add convexity/unique-action, fresh-workspace, deterministic replay, ordered
   parallel aggregation, and legacy-prefix instrumentation slices one at a
   time. Run only their targeted tests after each slice.
4. Run related regression tests and round preflight. Freeze the seal only when
   source identity, dependency fingerprint, settings, cases, comparison, and
   decision tree are complete.

## Formal execution and outcome tree

- `INVALID-SOLVER-REPAIR`: any seal, source, dependency, case, trace,
  comparison, or replay guard fails. No scientific estimate is admissible.
- `SOLVER-REPAIR-NO-GO`: convexity, unique-action, prefix agreement,
  development completion, residual, or deterministic replay fails. Holdout
  remains inaccessible.
- `DEVELOPMENT-NO-GO`: solver adequacy passes but either unchanged R325
  development performance gate fails. Holdout remains inaccessible.
- `FRESH-HOLDOUT-NO-GO`: development admission passes but any holdout arm has a
  solver, execution, finite-value, residual, or physical-constraint failure.
- `RETAINED-BLOCK-NO-VALUE`: the holdout is valid but the unchanged absolute or
  retained-versus-deleted directional performance gates fail.
- `CONSTRAINED-HORIZON-PASS`: every solver-adequacy, development, holdout, and
  retained-versus-deleted gate passes. This authorizes only the next separately
  sealed physical closed-loop question; it does not authorize agents or
  training.

## Scope limits and stopping conditions

- Model-only Windows execution. No ANDES, physical closed loop, plant change,
  reward, distributed runtime, agent implementation, or neural training.
- No weight, horizon, case, threshold, solver-setting, seed, or outcome search
  after the formal seal. No reinterpretation or mutation of R325 artifacts.
- EVAL is not applicable because this round has no trained policy or physical
  trajectory. It remains reserved for later closed-loop evidence as a
  diagnostic, never as formal authority.
- The conference title remains exactly `Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning`; R326 cannot support
  its distributed-agent or learning terms.

## Cross-references

- Direct question: `memory/questions/Q-0080.md`.
- Blocking negative result: `memory/claims/CLM-0835.md` and
  `paper/decoupling_marl_model_first/reports/R325.md`.
- Frozen predecessor seal and execution:
  `memory/rounds/R325/constrained_horizon_seal.json` and
  `results/r325_constrained_horizon/execution.json`.
