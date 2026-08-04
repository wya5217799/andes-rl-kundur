---
round: R331
state: aborted
opened: '2026-08-04'
closed: '2026-08-04'
supersedes_rounds: []
superseded_by_round: null
abort_reason: publication gate found incomplete red tests and imprecise evidence locators
superseded_note: null
---
# R331 plan - ANDES bridge reconciliation and platform judgment

## TL;DR

Answer Q-0084 before any closed-loop ANDES execution. Reconcile the exact R329
reduced-model estimator-controller package with the current model-first ANDES
implementation and installed ANDES 2.0.0 definitions: state and output
endpoints, action path, units and bases, signs, sample order, disturbances,
initialization, and every active feasibility limit. Use official documentation
and installed first-party source only for platform semantics. Issue one
prospective `ALLOW`, `QUALIFY`, or `BLOCK` judgment for a separately sealed
minimal deterministic ANDES bridge. Do not run a physical closed loop, change
the R329 package, design agents or rewards, train, or invoke EVAL.

## Authority and workflow

- Direct question: `memory/questions/Q-0084.md`.
- Scientific authority: the selected manuscript `LINE.md`, its model contract,
  CLM-0860, and the R330 feed/results pointers.
- Workload: `evidence`, because this round may dispose a registered question
  and authorize or block a later physical experiment.
- Research Supervisor route: one bounded primary-source `research` task, not a
  literature landscape. Official ANDES documentation and installed source are
  context evidence, not measurement-of-record.
- Ask Matt route: `diagnosing-bugs`, with the scientific acceptance criterion
  below and a fast static contract checker as the feedback loop. Engineering
  checks return evidence to this gate and cannot authorize execution alone.

## Methodology

### Frozen reconciliation inventory

The analysis must contain one row for every item below, with the reduced-model
meaning, current implementation locator, official model/source locator, unit,
base, sign, sample time, disposition, and any claim-ceiling consequence:

1. platform class and phenomena represented or omitted;
2. 100-MVA system base, device bases, and physical 60-Hz frequency base;
3. controlled proxy identity, storage identity, and source-to-readback index;
4. measured output vector and the distinction between requested, projected,
   internally limited, and achieved active power;
5. node action and edge-to-node action signs, including the legacy opposite-
   sign incidence exclusion; the estimator's executed-input return path is the
   inverse transform of the externally projected node command, not the planned
   request or lagged achieved power, and requires an induced-projection test;
6. external command projection, power/current/voltage capability, ramp, SOC,
   one-step energy, efficiency, recovery limits, and the installed storage
   model's non-symmetric behavior at the lower power-comparator boundary;
7. ESD1 active-current lag and the sign of charging, discharging, SOC change,
   and grid injection;
8. 0.2-s controller hold, TDS substeps, pre-disturbance first observation, and
   the one-sample causal delay; the later physical seal must reject any
   inherited N_SUBSTEPS override, pin five 0.04-s wrapper segments, and record
   the actual simulator time grid separately;
9. operating-point construction, disturbance application, initialization,
   disabled stochasticity, and unchanged physical topology;
10. reduced latent-state status: estimator-internal coordinates rather than
    direct physical state readbacks, with delivered outputs and executed input
    as the only runtime bridge.

No endpoint may be accepted from a variable name alone. Each material mapping
must be supported by executable source and, where ANDES owns the semantics, an
official document or installed first-party source definition.

## Fast failure detector

- Build one deterministic static checker over a frozen reconciliation record.
  It must fail on a missing inventory row, unresolved unit/base/sign/timing
  field, unsupported source locator, hidden M/D write, use of a requested value
  as achieved power, wrong action-incidence sign, or an over-ceiling platform
  claim.
- The inherited environment-variable override for the wrapper segment count is
  an explicit later-seal qualification, not an accepted hidden degree of
  freedom. Likewise, a later bridge must either keep charging commands strictly
  inside the installed lower comparator boundary with a frozen margin or
  reproduce the installed zero-below-lower behavior exactly.
- Before any implementation repair, demonstrate the checker is red-capable
  with targeted tests that inject each failure class. Keep this loop local and
  seconds-fast; no ANDES simulation is needed.
- Read-only inspection of the WSL-installed ANDES 2.0.0 package is permitted.
  Modifying the installed package, model-first plant, protected environments,
  R329/R330 assets, or any sealed source is forbidden.

## Prospective decision tree

- `INVALID-BRIDGE-RECONCILIATION`: source identity, exact inventory, locator,
  official-source, checker replay, or no-execution/no-training guard fails.
- `BLOCK`: at least one load-bearing endpoint, unit/base, sign, sample-order,
  disturbance, initialization, or feasibility-limit mismatch is unresolved;
  the implemented plant cannot represent a phenomenon needed by the declared
  phasor-domain experiment; or the bridge would require changing the frozen
  R329 estimator/controller after result access.
- `QUALIFY`: the bridge is internally executable and every load-bearing
  mapping is explicit, but one or more declared modelling assumptions or
  platform omissions require a narrower claim ceiling and an explicit guard
  in the later seal. The qualification may not be repaired by wording alone.
- `ALLOW`: every load-bearing mapping is exact or guarded with no unresolved
  material assumption beyond the already declared phasor-domain scope. Only a
  separately reserved and sealed deterministic ANDES bridge becomes eligible.

`QUALIFY` or `ALLOW` does not prove controller performance. It may close Q-0084
and open one minimal physical-bridge question. `BLOCK` closes Q-0084 negative
and returns to the smallest identified implementation or modelling repair.

## Comparison and claim ceiling

This round compares no controller arms and estimates no performance effect.
The comparison-identifiability gate is therefore not yet applicable; it must
run before the later reduced-model-versus-ANDES estimand is frozen. The maximum
claim here is platform and interface suitability for one prospectively sealed
phasor-domain electromechanical simulation. EMT, switching transients,
hardware, field deployment, safety, stability, topology generalization,
distributed execution, agent value, reward value, and learning value remain
outside scope.

## Verification and stopping conditions

- Targeted tests cover every red-capable failure class and the exact accepted
  inventory; deterministic analysis replay is byte-identical apart from an
  allowed creation timestamp.
- Run round preflight before implementation, then targeted tests during each
  slice. At close run the feed publication gate, feed checker, ledger
  validation, render, repository health, whitespace check, and the complete
  test suite once.
- Stop without physical execution after the judgment. A later ANDES bridge
  requires a new round, immutable bank, sealed sources and thresholds, WSL-only
  execution through `scripts/andes_scratch.py`, and no outcome-dependent
  redesign of R329.
- Preserve the conference title exactly. No distributed runtime, reward,
  agent, training, or EVAL work is authorized in R331.

## Asset protection

- Preserve R306-R330 plans, seals, results, feeds, claims, questions, verdicts,
  protected environments, installed ANDES, and the R329 package byte-for-byte.
- New durable assets are limited to the R331 plan, one formal reconciliation
  checker, focused tests, a frozen reconciliation/analysis artifact with
  sidecar, one feed, one claim, one verdict, Q-0084 disposition, and current
  line navigation refresh. Background research notes remain temporary unless
  the final gate demonstrates a durable manuscript need.

## Cross-references

- `memory/questions/Q-0084.md`
- `paper/decoupling_marl_model_first/working/model_contract.md`
- `memory/claims/CLM-0860.md`
- `paper/decoupling_marl_model_first/reports/R330.md`
