---
round: R330
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R330 plan - untouched holdout and output-mismatch gate

## TL;DR

Answer Q-0083 by executing the exact R329 retained estimator-controller package
on the untouched registered holdout: sixteen separated-doublet base cases under
five fixed delivered-output mismatch modes, for eighty rows. Reconstruct the
R329 estimator and controller only from their sealed sources, verify their
matrix fingerprints before any holdout row, and permit no resynthesis choice,
retuning, fallback, repair, or result-dependent branch. Compare each controlled
row with zero control under the same plant, disturbance, delivered-output
mismatch, and score. No ANDES, physical closed loop, cross-deleted arm,
distributed runtime, agent, reward, training, or EVAL execution is authorized.

## Snapshot at plan-time (oracle as of 2026-08-04)

<!-- Auto-injected equivalent to the reservation snapshot. -->

### Open questions

- Q-0004 - AndesBaseEnv absorb-into-V4 verification.
- Q-0026 - archive-index query signal.
- Q-0083 - untouched double changes under registered measurement distortions.

### Recently closed

- Q-0082 - closed positive by CLM-0855 in R329.
- Q-0081 - closed positive by CLM-0850 in R328.
- Q-0080 - closed positive by CLM-0845 in R327.

## Methodology

### Frozen execution contract

- Parents are the immutable R326 holdout definition and the complete sealed
  R329 estimator package, execution, analysis, claim, and feed. Before seal,
  record SHA-256 fingerprints for every R329 estimator and controller matrix;
  before holdout, deterministic reconstruction must reproduce them exactly.
- Generate exactly the R326 `separated_doublet` holdout cases: two registered
  operating points, four disturbance coordinates, two signs, and one initial
  SOC, giving sixteen base cases. Cross them with exactly five registered
  mismatch modes: nominal, plus scale, minus scale, signed reflection, and
  common-differential exchange.
- A mismatch changes only the delivered and scored output by the frozen linear
  transform. Both controlled and zero-control denominators use the same
  transform. Plant state dynamics, disturbance, initial condition, and action
  path remain unchanged.
- At controller step `k`, the fixed estimator receives only internal memory,
  delivered `y[k-1]`, executed `u[k-1]`, and frozen retained matrices. Current
  output, true reduced-model latent state, disturbance, future data, case
  outcome, and zero-control score do not enter the estimator or controller.
- Keep the R329 objective, horizon, scales, sparse solver and settings, warm
  starts, action map, power/ramp/SOC limits, information interface, and
  conference title unchanged.
- Execute two complete canonical eighty-row passes with at most eight workers,
  one native numerical thread per worker, a fresh solver per row, worker-only
  computation, and parent-only ordered serialization. The passes must be
  byte-identical.

## Comparison-identifiability gate

Decision: ALLOW for one bounded holdout estimand.

- Each controlled/zero pair shares operating point, disturbance, initial SOC,
  plant, output mismatch, delivered-output definition, horizon, and score. The
  controlled arm alone uses the frozen constrained action, so the identified
  estimand is this single R329 package's output-score change relative to zero
  control on the registered holdout.
- R330 does not compare estimator classes, old versus new observers,
  cross-block retention versus deletion, centralized versus distributed
  execution, or learning versus deterministic control. It therefore cannot
  attribute value to estimator architecture, decoupling, coordination,
  agents, or learning.
- Output-mismatch modes are registered linear score/measurement perturbations,
  not sensor-noise distributions, nonlinear plant mismatch, or physical
  simulator evidence.

## Formal outcome tree

- `INVALID-ESTIMATOR-HOLDOUT`: any source, parent, development identity,
  fingerprint, exact inventory, mismatch identity, information-boundary,
  deterministic replay, finite-trace, solver-residual, constraint, or analysis
  replay guard fails.
- `ESTIMATOR-HOLDOUT-NO-GO`: execution is valid but aggregate mean regulated-
  output ratio exceeds `0.98`, aggregate worst ratio exceeds `1.0`, or any of
  the eighty rows is not below zero control.
- `ESTIMATOR-HOLDOUT-PASS`: every guard passes, aggregate mean is at most
  `0.98`, aggregate worst at most `1.0`, and all eighty rows beat zero control.
  Mismatch-mode summaries are descriptive and cannot change this rule.
- A pass closes Q-0083 only for the frozen reduced-model holdout and may open a
  separate physical reduced-model-versus-ANDES execution gate. A no-go closes
  this fixed estimator package for holdout robustness and returns to a new
  development-only diagnosis; holdout outcomes may not tune it.

## Red-green seams and verification

- Seam one: a pure holdout classifier must distinguish valid pass, valid no-go,
  invalid inventory, invalid information use, and invalid numerical traces from
  caller-visible payloads and the sealed contract.
- Seam two: the execution adapter must expose the exact eighty-row contract,
  verify frozen design fingerprints, run two complete holdout passes, and keep
  every learning, physical, and EVAL path unreachable.
- Write one failing behavior test before each minimal implementation slice.
  Before seal run the R325-R330 related regressions, lint, preflight, and
  whitespace checks. After seal no source, case, mismatch, threshold,
  comparator, or classification change is permitted.

## Asset protection and stopping conditions

- Add only one R330 classifier, one thin holdout adapter, tests, seal, and R330
  artifacts. Do not mutate R326-R329 sources, contracts, results, claims, or
  feeds.
- The holdout is opened once only after a valid seal. A failed row, mode, or
  gate does not authorize rerun with changed estimator or controller settings.
- No physical-state interpretation, frequency-restoration, transient-
  stability, safety, topology-generalization, deployment, coordination,
  distributed-agent, reward, learning, or title-result claim is eligible.
- EVAL remains diagnostic-only and is not informative because no learned or
  distributed policy is under examination.

## Cross-references

- Direct question: `memory/questions/Q-0083.md`.
- Frozen repair: `memory/claims/CLM-0855.md` and
  `paper/decoupling_marl_model_first/reports/R329.md`.
- Frozen estimator artifacts: `memory/rounds/R329/disturbance_estimator_seal.json`
  and `results/r329_disturbance_estimator/`.
- Registered holdout origin: `memory/rounds/R326/solver_adequacy_seal.json` and
  `scripts/run_r325_constrained_horizon.py`.
