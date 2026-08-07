---
round: R359
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R359 plan - exact-observation causal residual design

**Opened**: 2026-08-07
**Driver**: Test whether R358's physically admissible offline residual can be
selected causally from the exact information available to future edge agents.
**Parent**: Q-0096; CLM-0940; CLM-0925; R358; R352

## TL;DR

Workload: `evidence`. Freeze one non-neural, independently executed three-edge
residual controller whose inputs and governor exactly match the future agent
interface. Use R358 only for development targets, keep the R352 residual
holdout labels sequestered, and stop before any neural training, new simulator
trajectory, or formal attempt until implementation and readiness pass.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0096 [opened R359] Can one fixed causal neighbour-local residual controller recover the R358 physical headroom using exactly the future agents' information and three-edge action path?

## Recently Closed (last 3)

- Q-0095 closed-positive @ R358, by CLM-0940 — Do any exposed R356 candidates retain the unchanged joint target under the exact three-edge physical limits?
- Q-0094 closed-negative @ R356, by CLM-0930 — Does the matched neighbour-local deterministic baseline leave material, neighbour-observable, and physically feasible residual headroom?
- Q-0093 closed-positive @ R352, by CLM-0925 — Does a tuned endpoint-local three-edge deterministic controller retain differential-synchronization value on an untouched disturbance-shape bank?

## Methodology

### Research Supervisor design gate

- **Decision question**: can one fixed causal endpoint-neighbour residual law
  recover material endpoint benefit over the frozen R352 local controller?
- **Primary comparison**: the frozen `r352_distributed_controller_loop_v2`
  selected-local controller versus the same controller plus the fixed R359
  neighbour-local residual. Zero residual is the matched control condition.
- **Diagnostic only**: exact physical offline optima establish attainable
  per-case headroom and holdout strata but cannot enter the deployed
  controller, its fit, or the primary causal attribution.
- **Identified estimand**: paired finite-bank counterfactual effect of adding
  this one fixed affine residual controller to the R352 base controller under
  the same local information, action, physical path, timing, and endpoints.
- **Comparison-identifiability decision**: `QUALIFY`. The comparison identifies
  the executed controller addition, not neighbour information sufficiency,
  nonlinear policy value, multi-agent value, or an algorithm-family effect.

### Frozen parent and split

- Development is the sixteen R352 ramp-hold zero/selected-local pairs already
  exposed to R353-R358. It supplies causal features and R358 labels only.
- The ten R358 accepted physical witnesses supply development residual targets.
  The six accepted relaxed-infeasible cases supply all-zero negative-control
  targets; they are not relabelled as feasible and their certificates remain
  authoritative.
- Holdout is the sixteen R352 staggered-rise zero/selected-local pairs. Their
  parent endpoints are already public, so they are a sequestered residual-label
  confirmation bank rather than an unseen-plant generalization sample. No
  R359 holdout oracle, residual proposal, counterfactual endpoint, or gate may
  be read before the development stop and frozen full-development fit pass.
- The R341 order-12 separate-input point models, response-map construction,
  R352 physical traces, R358 targets, and all parent hashes are immutable.

### Exact information contract

Each of the three edge actors receives one complete `LocalEdgeObservation` at
the causal pre-action instant. Its numeric vector has exactly fifteen fields:

1. two endpoint frequency deviations;
2. two endpoint RoCoFs;
3. its own previous executed edge flow;
4. two endpoint previous commanded powers;
5. two endpoint states of charge;
6. two endpoint voltages;
7. two endpoint lower residual-power bounds; and
8. two endpoint upper residual-power bounds.

Edge identity is fixed by the independently instantiated actor and is not an
outcome feature. Achieved power, point, disturbance channel, sign, scenario
identifier, other-edge observations, joint/common/differential coordinates,
future values, realized endpoints, and oracle values from the evaluated case
are forbidden. Lower/upper bounds must be reconstructed through the same
physical contract used by R352, not copied from an offline optimizer.

R352 traces do not preserve enough pre-action history to reconstruct the first
two RoCoF-bearing actions exactly. Both development targets and every proposal
therefore fix action indices zero and one to zero and exclude those rows from
fitting. This is a causal limitation, not a post-result exclusion.

### Matched action and physical contract

- Each actor emits one normalized scalar in `[-1, 1]`; the ordered action is
  the three independent edges `(0,1)`, `(1,2)`, `(2,3)` with no central scalar
  projection or cross-edge aggregation.
- The residual is converted by the unchanged `0.05` system-pu magnitude and
  slew path, then added over the R352 base command through the same incidence,
  endpoint-headroom allocation, node power/ramp, energy, efficiency,
  state-of-charge, voltage/current, limiter, and readback guards.
- Proposed, executed, and achieved actions remain distinct. Only executed
  actions enter counterfactual endpoint evaluation and physical guards.

### Fixed controller and leakage barrier

- Fit one standardized affine least-squares map per edge. Normalize the R358
  physical edge-flow targets by the frozen edge limit before fitting; clip only
  at the public normalized-action boundary. No regularizer, architecture,
  hyperparameter, random seed, reward, or candidate sweep exists.
- Development predictions are leave-one-scenario-out: every scenario's target
  is excluded from all three edge fits that predict it.
- The formal controller is fitted once on all development rows after the
  development gate. Its coefficients, standardization constants, source
  hashes, and holdout predictions are written create-only before any holdout
  oracle label or counterfactual endpoint is read.
- Action-vector error is diagnostic only because physical optima need not be
  unique. Scientific gates use endpoint consequences after the exact physical
  projection.

### Endpoints and decision tree

The scenario is the analysis unit. Lower is better for both common-coordinate
IAE and differential-coordinate energy. For each candidate and endpoint keep
the R353 thresholds unchanged: paired mean improvement at least `0.02`, a
one-sided 95-percent paired upper bound below zero, every point/channel/sign
subgroup mean below zero, and maximum single-scenario ratio no greater than
`1.05`.

Development must pass complete inventory, exact-information construction,
leave-one-scenario-out physical projection, both nominal endpoint gates, and
the frozen model-mismatch gates before holdout residual labels are read. The
formal holdout additionally requires the once-fitted controller hash,
holdout-model adequacy, complete physical and information guards, both nominal
endpoint gates, and both mismatch-bounded endpoint gates.

- `NEIGHBOUR-CAUSAL-PROBE-ELIGIBLE`: every integrity and scientific gate
  passes. This permits one separately registered non-learning physical
  residual intervention only; training stays false.
- `NO-NEIGHBOUR-CAUSAL-HEADROOM`: execution is valid but at least one
  scientific gate fails. This rejects this fixed affine formulation only and
  authorizes no holdout repair, training, or simulation.
- `ANALYSIS-INVALID`: any source, parent, inventory, information, causality,
  leakage, numerical, process, or artifact guard fails. Preserve the attempt
  and do not retry in place.

### Ranked vulnerability ledger and prospective repairs

1. **Blocking - information mismatch**: the historical 13-field proxy included
   achieved power and omitted future-interface headroom bounds. R359 replaces
   it with the exact 15-field public observation and tests field-level
   invariance against forbidden values.
2. **Blocking - startup noncausality**: the first two complete pre-action
   histories are unrecoverable. R359 fixes their residual actions to zero
   before fitting and evaluation.
3. **Blocking - holdout leakage**: known parent endpoints could invite
   outcome-driven repair. R359 has one no-tuning map, create-only coefficient
   and prediction artifacts, and a development stop before any R359 holdout
   residual label is read.
4. **High - non-unique oracle actions**: action imitation can falsely reject a
   useful controller. R359 uses endpoint consequences as primary and keeps
   action error diagnostic-only.
5. **High - six infeasible development cases**: missing positive targets could
   be silently dropped. R359 keeps all six as explicit zero-residual negative
   controls and reports positive/infeasible strata separately.
6. **Medium - model-class overreach**: one affine map cannot represent all
   causal policies. Any negative result is bounded to this formulation; no
   impossibility, neural, or multi-agent claim is permitted.
7. **Medium - finite exposed topology**: the banks cover one topology and two
   exposed operating points. No population, topology, stability, safety,
   robustness, hardware, or deployment language is permitted.

### Handoff to Ask Matt

- **Scientific acceptance criterion**: exact public information ownership,
  independent normalized edge actions, leakage-proof development/holdout
  separation, unchanged physical projection, and a pure three-way classifier.
- **Implementation dependency**: one reusable exact-observation vectorizer and
  fixed affine edge controller; one R359 conclusion probe; one stable
  create-only execution adapter; focused tests.
- **Authorized write scope**: Q-0096/R359 plus new R359 implementation seams
  and tests. R341/R352/R353-R358 sources and evidence remain byte-unchanged.
- **Engineering deliverable**: `rehearsal`, `prepare`, and `analyse` entrypoints
  whose same pre-attempt path verifies exact parent/source closure and cannot
  expose a simulator, training, reward, or alternate-output command.
- **Verification**: red-green focused tests, compilation, `git diff --check`,
  and `python memory/tools/round_preflight.py R359`.
- **Return gate**: Research Supervisor Design. Passing engineering checks
  proves implementability only; it does not authorize seal or execution.

### Execution status

`HOLD`. This turn may implement and verify the offline entry but may not create
a rehearsal, seal, formal attempt, formal result, holdout residual label, new
physical-simulator trajectory, or training output. A later Readiness gate must re-check the
finished implementation, parent closure, output absence, and whole-host budget.

## Formal launch contract

- formal_entry: `python scripts/run_r359_neighbour_causal_residual.py analyse --expected-seal-sha256 <sha256>`.
- rehearsal_command: `python scripts/run_r359_neighbour_causal_residual.py rehearsal`.
- rehearsal_scope: same-pre-attempt-path; exercise the exact formal pre-attempt verification path
  over plan/question identity, complete R352/R358 parents, exact development
  and holdout identities, exact-observation field ownership, startup masking,
  coefficient/prediction leakage barriers, synthetic positive/negative/invalid
  classifier cases, installed dependencies, and output absence without
  reading a holdout residual label or creating an attempt or result.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- worker_processes: 1
- native_threads_per_process: 1
- wsl_python_processes: 0. Formal offline stages are serial and create-only.
- capacity_evidence: `memory/rounds/R359/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
  The measured development-only dry probe completed all sixteen records in
  `0.627362200000789` seconds in one Windows process with one native thread;
  the serial cap is intentional because the stages are dependent and the
  complete offline run is quick. Any active conflicting manuscript process,
  missing dependency, or source drift returns `HOLD`.
- Formal completion is one immutable staged `analysis.json` plus manifest and
  sidecars, or one immutable `failure.json` plus sidecar. Retry is forbidden.

## Gate

Design passes only when the exact 15-field information vector, independent
normalized actions, development/holdout leakage barrier, startup mask,
physical projection, endpoint gates, three-way classifier, source closure, and
focused tests are all explicit and executable. Any missing field ownership,
privileged feature, action mismatch, outcome-dependent choice, or incomplete
negative control returns `BLOCK` before rehearsal or seal.

## Asset protection contract

R341/R350/R351/R352/R353/R354/R355/R356/R357/R358 plans, questions, claims,
sources, rehearsals, seals, attempts, results, traces, manifests, feeds,
verdicts, thresholds, and line evidence remain byte-unchanged. Add only Q-0096,
the R359 plan, one exact-observation implementation seam, one R359 probe, one
stable adapter, focused tests, and later separately authorized R359 artifacts.
Do not edit another manuscript line, start learning or a physical simulator, change the
working title, or push publicly.

## Cross-references

- Q-0096
- CLM-0940 / R358 physical action-space headroom
- CLM-0925 / R352 matched neighbour-local deterministic controller
- R353 exact causal split and gate grammar, without inheriting its 13-field
  information mismatch or invalid solver attempt
