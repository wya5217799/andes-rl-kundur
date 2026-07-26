---
round: R270
state: completed
opened: '2026-07-25'
closed: '2026-07-25'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R270 plan — controller-agnostic attainable-margin library oracle

**Status**: ACTIVE
**Opened**: 2026-07-25
**Driver**: Q-0032 after R269 blocked reward-based retraining
**Parents**: CLM-0545, CLM-0550
**Prospective claim slot**: CLM-0555

## TL;DR

Measure whether the current VSG inertia/damping inputs contain a useful
physical margin above droop before any more learning.  Freeze eight
physics-interpretable early-transient residual schedules spanning the complete
local basis of common/inter-area inertia/damping signs, evaluate all of them on
the eight R268 feasible disturbances, and let a disturbance-informed library
oracle choose the best safe joint-improving schedule per scenario.  This is an
optimistic actuation diagnosis, never a deployable policy.

## Falsifiable objective

Determine whether the current bounded inertia/damping actuation admits a
nontrivial controller-agnostic physical improvement margin above tuned droop
on reference-feasible disturbances before any further learned controller work.

## Methodology

### Fixed baseline and envelope

- Reuse the exact eight R268 development scenarios:
  each of `PQ_0`, `PQ_1`, `PQ_Bus14`, and `PQ_Bus15` at `-1.5` and `+1.5`.
- Reuse the immutable R268 `droop_k10` trace for each scenario.  Verify
  completion, 150 steps, scenario identity, and SHA-256 before interpreting
  candidates.
- V4 paper-faithful environment, seed 42, 150 steps, real ANDES in WSL.
- Do not use the R268 learned residual, a neural network, or any training.

### Frozen action library

For the first 15 control steps only (3.0 s at 0.2 s/step), compose

`u_exec = clip(u_droop(k=10) + 0.25 * b, -1, 1)`.

After step 14, execute pure droop.  The eight fixed basis/sign schedules are:

1. `common_M_pos`: `b_M=[+1,+1,+1,+1]`;
2. `common_M_neg`: `b_M=[-1,-1,-1,-1]`;
3. `common_D_pos`: `b_D=[+1,+1,+1,+1]`;
4. `common_D_neg`: `b_D=[-1,-1,-1,-1]`;
5. `area_M_pos`: `b_M=[+1,+1,-1,-1]`;
6. `area_M_neg`: `b_M=[-1,-1,+1,+1]`;
7. `area_D_pos`: `b_D=[+1,+1,-1,-1]`;
8. `area_D_neg`: `b_D=[-1,-1,+1,+1]`.

All unspecified action components are zero.  `[1,1,-1,-1]` follows the
environment's frozen `AREA_OF_AGENT=[1,1,2,2]`.  The basis spans both signs of
common and inter-area directions for both available actuators.  Amplitude
0.25 uses 25% of normalized action travel and is fixed before trajectories;
the short window keeps nominal added L1 effort at 0.75 agent-seconds for a
single active component.

Strict new-trajectory budget: exactly `8 scenarios × 8 schedules = 64`.
No amplitude, duration, combination, second basis, or adaptive optimizer may
be tried after seeing results.

### Physical summaries and per-scenario eligibility

Use the existing 60-Hz physical endpoint summarizer.  For each candidate and
its matched droop trace, report:

- VSG-mean IAE and normalized synchronization loss;
- worst-bus peak and max sampled RoCoF;
- settling at the 0.05-Hz band;
- action L1, total variation, and saturation;
- completion/TDS failure.

A candidate is oracle-eligible for a scenario only if:

1. it completes all 150 steps and settles;
2. both co-primary endpoints are no worse than matched droop;
3. worst-bus peak and max RoCoF are each no worse than `+5%`;
4. action L1 and action total variation are each no worse than `+25%`;
5. action saturation fraction is not higher than droop.

### Frozen library-oracle selection

For each scenario, choose the eligible candidate with minimum

`common = mean_t(abs(mean_i(df_physical))) / 0.05`

plus

`differential = mean_t(mean_i((df_physical-mean_i(df_physical))^2)) / 0.05^2`.

If no non-droop candidate is eligible, choose droop.  Ties go to droop, then
the candidate order listed above.  Selection deliberately sees the entire
scenario outcome; it is an optimistic upper bound for this fixed library and
cannot be presented as a deployable controller.

## Pre-registered outcomes and decision gate

### MATERIAL-MARGIN

All conditions must hold:

- the library oracle chooses a non-droop schedule in at least 4/8 scenarios;
- oracle mean VSG-mean IAE improves by at least 2.0% versus droop;
- oracle mean normalized synchronization loss improves by at least 2.0%;
- every selected trajectory satisfies the completion, settling, safety,
  action, and saturation eligibility guards;
- all baseline hashes and evaluation sources verify.

This retains the actuation problem and routes future work to
observability/credit assignment.  It does not validate a learned controller.

### NO-MATERIAL-MARGIN

Every other valid result.  Close learned inertia/damping controller
development on the current modified Kundur environment.  Do not try another
amplitude, duration, schedule combination, reward, or neural architecture.
The scientifically defensible pivot is then benchmark/model validity, a
different actuator, or a different system—not algorithm search.

### INVALID

Baseline drift, source/contract drift, missing trajectory, non-finite endpoint,
runner error, or more/fewer than 64 requested candidate trajectories.  Repair
only the integrity defect and rerun the identical contract.

Candidate failures do not invalidate the audit; they are recorded as
ineligible actuation directions.  No failed row is deleted or replaced.

The 2% threshold is fixed as a materiality screen substantially above R268's
approximately 0.1% adverse differences.  This small deterministic library
oracle does not support population intervals or confirmatory claims.
`cum_rf_total` is reported as the historical synchronization-only diagnostic;
`geo` is not used or optimized.

## Asset protection and scope limits

- Add one standalone scheduled-basis controller module, one evaluator, and
  focused tests; reuse the existing runner and physical summaries.
- Do not change V4, `base_env.py`, residual training adapter, learning agents,
  training code, R268/R269 evidence, historical checkpoints, paper metrics,
  manuscript files, or figures.
- Do not train, tune, sweep, add a ninth candidate, or run a second bank.
- Do not claim topology generalisation, stability certification,
  cross-simulator transfer, or deployability.

## Verification

- `python memory/tools/round_preflight.py R270 --json`;
- focused scheduled-controller/evaluator tests;
- `python -m pytest tests -q`;
- real-ANDES one-trace smoke after tests and preflight;
- exactly 64 formal WSL candidate trajectories;
- `python memory/tools/dual_metric_lint.py --claim CLM-0555`;
- `python memory/tools/validate.py`;
- `python memory/tools/render.py`.

## Planned outputs

- `src/andes_rl_kundur/evaluation/attainable_oracle.py`;
- `scripts/eval_attainable_oracle.py`;
- `tests/test_attainable_oracle.py`;
- `results/r270_attainable_oracle/`;
- R270 logs, CLM-0555, Q-0032 update, verdict;
- no training, manuscript, or paper-figure artifacts.

## Cross-references

- CLM-0535: the hand-designed gate/smoother family closed.
- CLM-0550: corrected R268 learned-residual NO-GO and reward diagnosis.
- CLM-0545: objective audit blocked retraining and opened the attainability
  question.
- Q-0032: current controller-agnostic feasibility question.
