---
round: R328
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R328 plan - retained-arm state-estimation causal diagnosis

## TL;DR

Answer Q-0081 for the retained-cross controller with one information-only
intervention. Preserve the R327-valid retained plant, finite-horizon objective,
specialized solver, action map, physical limits, cases, and gates. Replace only
the corrected observer estimate by the exact delay-augmented state available in
the model-only simulation. Compare the new oracle diagnostic with the immutable
R327 output-feedback result. Never execute the cross-deleted oracle, holdout,
physical simulator, distributed runtime, agent, reward, or training path.

## Why this diagnosis is bounded

- R327 validly rules out candidate solver failure, residual failure, explicit
  actuator-constraint violation, and missing numerical equivalence, yet the
  retained-cross controller's development mean and worst ratios remain far
  above their absolute gates.
- Scratch motivation only: on the retained plant, exact-state substitution with
  every other field fixed reduced all 32 development ratios below one. This
  selects the prospective intervention but is not evidence and determines no
  R328 verdict.
- The retained synthesis model and retained executed plant are the same
  realization, so their state coordinates are identical. The cross-deleted ERA
  realization has a different state basis; injecting the retained plant state
  into it is not an identifiable intervention and is explicitly prohibited.

## Methodology

### Frozen implementation contract

- Immutable parents: the R326 candidate execution and R327 seal, analysis,
  claim, and feed, all verified by their recorded SHA-256 digests.
- Single retained-cross arm and the exact 32 R326 development cases, nominal
  mismatch only. The zero-control denominators remain those in the immutable
  R326 rows.
- Exact state at sample `k` is the retained plant state concatenated with the
  actually delivered output from sample `k-1`, matching the frozen one-sample
  delay augmentation. This replaces only
  `estimate_prediction + filter_gain @ innovation` at the controller input.
- The sparse-QP implementation and settings, horizon, output/action scales,
  objective, warm start, node action map, power/ramp/SOC limits, disturbance,
  initial SOC, and plant update remain unchanged.
- Cases execute in fixed canonical order with at most eight workers, one native
  numerical thread per worker, fresh solver workspace per case, worker-only
  computation, and parent-only ordered serialization.
- Two full 32-case executions must be byte-identical after removal of the
  declared creation timestamp.

## Scientific acceptance criterion

- All 32 exact-state cases must complete with zero solver failures, execution
  errors, non-finite values, or explicit constraint violations. Maximum
  explicit residual must be at most `1e-8`; normalized primal and dual residual
  ratios must be at most one.
- The exact-state construction must match the retained delay-augmented model at
  every sample, and the retained plant/design state dimensions and matrices must
  be identity-matched by sealed hashes.
- The immutable R327 retained output-feedback arm must be valid and fail at
  least one unchanged absolute development gate.
- `ESTIMATION-LAYER-CAUSE`: exact-state mean ratio at most `0.98`, exact-state
  worst ratio at most `1.0`, and every case ratio below one while the immutable
  output-feedback arm fails. This identifies the observer/estimation layer as
  the cause of retained-arm admission failure under this model-only contract.
- `ESTIMATION-NOT-DOMINANT`: the execution is valid but any exact-state absolute
  gate fails. The finite-horizon objective/action path remains implicated.

## Comparison-identifiability gate

Decision: ALLOW for one diagnostic estimand with a strict claim ceiling.

- Both arms share the same retained plant, cases, disturbance, timing,
  objective, solver, horizon, action coordinates, limits, warm starts, and
  execution budget. Only the controller state source differs: delayed-output
  observer estimate versus exact augmented state.
- The identified estimand is the retained controller's estimation-layer loss
  on the registered development bank and whether exact state rescues the frozen
  absolute gates. Exact state is privileged oracle information; the result does
  not establish a deployable observer, distributed information pattern,
  controller superiority, physical efficacy, or safety.
- Stay out: cross-deleted exact-state comparison, general observer claims,
  estimator architecture choice, weight/horizon repair, topology
  generalization, and title support.

## Red-green implementation order

1. Add pure-decision tests for exact-state rescue, valid non-rescue, invalid
   execution, and forbidden holdout/cross-deleted data; observe the missing
   module failure.
2. Implement the minimal pure R328 classifier and exact-state trace summary.
3. Add a thin sealed adapter and tests that prove only retained development
   cases are reachable and the exact state is constructed from plant state plus
   previous delivered output.
4. Run related regressions, preflight, seal, two-pass execution, formal
   analysis, independent evidence/domain audits, feed publication, and closeout.

## Formal outcome tree

- `INVALID-ESTIMATION-DIAGNOSIS`: any source, parent, state-identity, case,
  trace, deterministic replay, residual, constraint, or holdout/cross-deleted
  exclusion guard fails.
- `ESTIMATION-NOT-DOMINANT`: the exact-state execution is valid but does not
  rescue every frozen absolute development gate.
- `ESTIMATION-LAYER-CAUSE`: the exact-state execution validly rescues the frozen
  retained absolute gates while the immutable output-feedback arm fails.

## Scope limits and stopping conditions

- Development-only, centralized, model-only oracle diagnosis. No R326/R327
  mutation, controller repair, new observer design, weight/horizon search,
  cross-deleted oracle, fresh holdout, ANDES, physical closed loop, plant
  change, distributed runtime, reward, agent, neural training, or EVAL run.
- No case, threshold, state definition, solver setting, comparison, or
  classification change after the formal seal.
- The conference title remains exactly `Decoupling-Oriented Coordination of
  Paralleled VSGs With Multi-Agent Reinforcement Learning`; R328 cannot support
  its coordination, distributed-agent, or learning terms.

## Cross-references

- Direct question: `memory/questions/Q-0081.md`.
- Blocking result: `memory/claims/CLM-0845.md` and
  `paper/decoupling_marl_model_first/reports/R327.md`.
- Immutable candidate traces: `results/r326_solver_adequacy/execution.json`.
- Formal solver/controller admission: `results/r327_reference_recovery/analysis.json`.
