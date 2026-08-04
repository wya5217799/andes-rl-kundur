---
round: R329
state: completed
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R329 plan - fixed disturbance-aware state estimator

## TL;DR

Answer Q-0082 with one fixed, development-only estimator that represents the
unknown input as a persistent hidden state. Preserve the R328-valid retained
model, constrained controller, cases, objective, solver, limits, thresholds,
and execution budget. At controller step `k`, use only the previous delivered
output, previous executed action, internal estimator memory, and frozen model
matrices to correct the previous hidden state and predict the current physical
state. Never expose current output, true state, or true disturbance to the
estimator. No candidate grid, holdout, physical simulator, distributed runtime,
agent, reward, training, or EVAL execution is authorized.

## Snapshot at plan-time (oracle as of 2026-08-04)

<!-- Auto-injected equivalent to the reservation snapshot. -->

### Open questions

- Q-0004 - AndesBaseEnv absorb-into-V4 verification.
- Q-0026 - archive-index query signal.
- Q-0082 - implementable hidden-state reconstruction for useful control.

### Recently closed

- Q-0081 - closed positive by CLM-0850 in R328.
- Q-0080 - closed positive by CLM-0845 in R327.
- Q-0078 - closed negative by CLM-0835 in R325.

## Methodology

### Fixed estimator

- For each retained operating point, augment the physical state by one
  four-coordinate unknown-input state. The frozen transition and measurement
  relations are `s=[x;d]`, `F=[[A,B],[0,I]]`, `G=[B;0]`, and `H=[C,D]` after
  subtracting the known executed-action feedthrough from the delivered output.
- Model the unknown-input state by one random-walk prior. Fix its change scale
  to the already registered disturbance scale `0.05`; fix measurement scale to
  one percent of the already registered output scales. Add only the existing
  trace-scaled numerical covariance floor. No covariance, gain, pole, or
  architecture candidate may be tried after the formal seal.
- Solve one steady-state discrete covariance equation per operating point and
  use its fixed gain. At step zero the declared reset state, delivered
  prehistory, executed action, and estimate are all zero. At later step `k`,
  correct the estimate of `[x[k-1];d[k-1]]` with delivered `y[k-1]` and executed
  `u[k-1]`, predict `[x[k];d[k]]`, and pass `[x_hat[k];y[k-1]]` to the unchanged
  constrained controller.
- The estimator API receives only the previous delivered output and executed
  action. True state and disturbance exist only in an audit trace outside the
  estimator and controller call graph.
- Scratch motivation only: this fixed construction passed the unchanged
  development performance floors without tuning and avoided exact direct
  inversion. That observation selects the prospective candidate but is not
  formal evidence and determines no R329 outcome.

### Structural and comparison gates

- Both augmented pairs `(F,H)` must have full observability rank fourteen. The
  covariance solution must be finite, symmetric, positive semidefinite, and
  satisfy the sealed normalized equation residual. The fixed gain must be
  finite and the corrected prediction-error spectral radius must be below one.
- The comparison-identifiability decision is ALLOW with a strict ceiling. R327
  delayed-output feedback, R328 exact-state oracle, and R329 fixed estimator
  share the retained plant, cases, objective, solver, horizon, action map,
  limits, timing, and execution budget. R329 changes only estimator state,
  covariance model, and gain. The estimand is whether this one permitted-signal
  estimator repairs retained development admission and reduces state-estimation
  error relative to the immutable failed parent.
- Exact state and disturbance may be read only by the row-level audit to score
  estimation error and information separation. Source/API guards must prove
  that neither enters estimator or controller computation.

### Frozen execution

- Use only the 32 retained development cases and immutable zero-control
  denominators. The R328 exact-state execution is a read-only upper comparator;
  the conditional holdout remains inaccessible.
- Keep the retained model, one-sample timing, specialized finite-horizon solver,
  horizon, objective, output/action scales, warm starts, action map,
  power/ramp/SOC limits, disturbances, initial conditions, thresholds, and
  conference title unchanged.
- Execute two complete canonical passes with at most eight workers, one native
  numerical thread per worker, a fresh solver per case, worker-only computation,
  and parent-only ordered serialization. The passes must be byte-identical.

## Formal outcome tree

- `INVALID-AUGMENTED-ESTIMATOR`: any sealed-source, parent, case-inventory,
  information-boundary, observability, covariance, stability,
  deterministic-replay, numerical, residual, constraint, holdout-exclusion, or
  oracle-identity guard fails.
- `AUGMENTED-ESTIMATOR-NO-GO`: the execution is valid but any unchanged
  absolute development gate fails, any case is not below zero control, or the
  aggregate state-estimation error is not lower than the immutable current
  observer under the matched audit.
- `AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS`: every structural and execution guard
  passes; aggregate state-estimation error is lower than the immutable current
  observer; mean regulated-output ratio is at most `0.98`, worst ratio at most
  `1.0`, and all 32 cases beat zero control.
- A development pass closes Q-0082 only for this fixed noiseless reduced-model
  information pattern and opens one separate prospective fresh-holdout
  question. A no-go returns to causal diagnosis without tuning or holdout
  access.

## Asset protection and stopping conditions

- Add only one pure estimator module, one R329 classifier, one thin adapter,
  tests, seal, and R329 artifacts. Do not mutate R326-R328 sources or results.
- R329 cannot establish robustness to output mismatch or noise, nonlinear
  physical behavior, distributed execution, learning, topology
  generalization, stability, safety, deployment, or support for the prospective
  title terms. Exact-state performance remains privileged diagnostic evidence.
- EVAL is not informative for this deterministic algebraic estimator round and
  is not run. It remains diagnostic-only and becomes eligible only under a
  separately registered learned or distributed-policy evaluation question with
  a frozen comparator.

## Cross-references

- Direct question: `memory/questions/Q-0082.md`.
- Causal parent: `memory/claims/CLM-0850.md` and
  `paper/decoupling_marl_model_first/reports/R328.md`.
- Immutable oracle: `results/r328_estimation_cause/execution.json` and
  `analysis.json`.
- Immutable valid failed parent: `results/r327_reference_recovery/analysis.json`.
