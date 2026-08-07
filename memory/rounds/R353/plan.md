---
round: R353
state: aborted
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: 'sealed analysis invalid: result serialization requested absent MinimumNormCertificate.message;
  failure artifact preserved; retry forbidden'
superseded_note: null
---
# R353 plan - matched neighbour-local residual-headroom gate

**Opened**: 2026-08-07
**Driver**: Re-test residual headroom after replacing the old global-information
deterministic parent with R352's matched neighbour-local three-edge baseline.
**Parent**: CLM-0925; Q-0094; R341 qualified point models; R350 gate grammar

## TL;DR

Freeze a create-only, non-learning analysis over R352's existing guarded
traces. Use ramp-hold records to construct and cross-check the residual target
and neighbour-local estimator, then apply the frozen estimator to the
staggered-rise residual holdout. A positive result permits only a later
non-learning physical residual intervention; training stays forbidden.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0093 closed-positive @ R352, by CLM-0925 — Does a tuned endpoint-local three-edge deterministic controller retain differential-synchronization value on an untouched disturbance-shape bank?
- Q-0092 closed-positive @ R351, by CLM-0920 — Can one deterministic three-edge controller execute from endpoint-only neighbour information through the future policy's exact physical governor?
- Q-0091 closed-negative @ R350, by CLM-0915 — Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?

## Methodology

**Lane**: evidence. R353 freezes a new comparator, holdout use, and formal
decision that can change training eligibility, although it creates no new
ANDES trajectory. No R352/R350/R341 asset may be modified.

### Research Supervisor design and comparison gate

- **Decision**: `ALLOW` for the bounded residual-over-baseline estimand.
- **Compared objects**: the frozen R352 selected neighbour-local controller;
  the same controller plus one offline-proposed zero-common three-edge residual.
- **Identified estimand**: paired counterfactual effect of one certified
  residual sequence or its fixed neighbour-local estimator over the R352 local
  baseline on the registered finite banks.
- **Matched factors**: same endpoint-neighbour information ceiling, three edge
  coordinates, action incidence, governor, magnitude/slew, device power/ramp/
  energy/state-of-charge limits, `0.2` second timing, point, disturbance, and
  endpoint definitions.
- **Required qualification**: the oracle sees the complete realized baseline
  output and is only an upper bound. The deployable estimator is one fixed
  standardized affine map per edge, not a policy-family representative.
- **Stay-out**: neural or multi-agent value, policy-class impossibility,
  physical residual benefit, stability, safety, robustness, topology,
  deployment, and title-term validation.

### Frozen inputs and split

- Parent source: R352 development and formal executions/manifests plus their
  zero and `kf500_kr0` selected-local trace files. The joint-information arm is
  rejected at inventory construction.
- Development: sixteen exposed ramp-hold pairs, two points, four load channels,
  and both signs. It may produce oracle targets, response-model innovation
  envelopes, and leave-one-scenario-out neighbour-local diagnostics.
- Holdout: sixteen staggered-rise pairs from the completed R352 formal bank.
  Their baseline endpoints are already public, but no R353 oracle residual,
  estimator prediction, counterfactual endpoint, or R353 gate was computed
  before this plan.
- Point models: the unchanged R341 order-12 separate-input realizations.
  Development observed local-minus-zero response innovations define a frozen
  per-point, per-coordinate maximum-absolute envelope. The holdout observed
  baseline action response must lie within that envelope plus `1e-8` absolute
  numerical tolerance or the model-adequacy gate fails.

### Residual and deployed information

- The oracle solves the existing independently certified three-start smooth
  convex problem for a minimum-norm 25-step edge residual atop the R352 local
  node-command path. It targets at least `0.02` improvement in both common-
  coordinate IAE and differential-coordinate energy and must pass original-
  unit power, ramp, energy, and state-of-charge limits.
- Each edge estimator receives only its two endpoint frequency deviations and
  RoCoFs, its own previous executed edge flow, endpoint previous achieved and
  commanded powers, endpoint state of charge, and endpoint voltages. Values
  are causal at the pre-action sample.
- R352 stores frequency after each action, so an exact pre-action RoCoF is not
  recoverable for the first two action indices. Those two residual actions are
  fixed to zero and their rows are excluded from estimator fitting; fitting
  and prediction begin only at index two, where the causal finite difference
  is exactly reconstructible from two completed parent samples.
- Forbidden estimator fields: point, disturbance channel, sign, scenario ID,
  future values, other-edge observations, joint coordinates, realized
  endpoints, and oracle outputs from the evaluated scenario.
- Estimator: one deterministic standardized affine least-squares map per edge,
  with no hyperparameter. Development uses leave-one-scenario-out proposals;
  the formal estimator is fit once on all development rows and applied without
  refit to holdout rows. Every proposal traverses the same physical headroom
  projection used by the oracle.

### Endpoints and decision

- Unit: scenario. Endpoints and lower-is-better direction are unchanged from
  R352/R350: common-coordinate IAE and differential-coordinate energy.
- For each endpoint and candidate, require paired mean improvement at least
  `0.02`, a one-sided 95% paired upper bound below zero, every point/channel/
  sign subgroup mean below zero, and maximum single-scenario ratio no greater
  than `1.05`.
- Development must pass certified oracle feasibility and neighbour-local
  leave-one-scenario-out nominal gates before holdout counterfactuals are read.
- Formal pass additionally requires complete parent inventory and hashes,
  holdout model adequacy, certified/physical oracle validity, local projection
  feasibility, and oracle/local nominal and mismatch-bounded endpoint gates.
- `RESIDUAL-PROBE-ELIGIBLE`: all gates pass; authorize one separately
  registered non-learning physical residual intervention only.
- `NO-TRAINING`: execution is valid but any scientific gate fails; close Q-0094
  negative for this formulation.
- `ANALYSIS-INVALID`: source, parent, inventory, causality, numerical,
  certificate, process, or artifact integrity fails; preserve the attempt and
  do not interpret direction.

### Handoff: Research Supervisor to Ask Matt

- **Current owner**: Ask Matt's test-first implementation route.
- **Required input**: this plan, CLM-0925/R352 parent artifacts, the R350 solver
  and gate seams, and the R341 qualified point-model loader.
- **Acceptance check**: loader admits exactly the 32 development and 32 holdout
  primary-arm traces; holdout labels/outcomes cannot enter fitting; local
  features contain only the declared endpoints and causal history; conclusion
  logic lives in `probes/`; no command runs ANDES or training.
- **Authority/write scope**: Q-0094/R353 plus one R353 probe, stable adapter,
  one artifact-independent public residual-headroom interface required by the
  repository executable boundary, and focused tests. Reuse existing package
  solver/model helpers without changing R341/R350/R352 assets or another
  manuscript line.
- **Return artifact**: tested create-only `rehearsal`, `prepare`, and `analyse`
  entrypoints with source/parent closure and staged development/holdout stop.
- **Return verification**: focused tests, Python compilation, `git diff
  --check`, and `python memory/tools/round_preflight.py R353`.
- **Next owner**: Model-first research owner for readiness/capacity, seal, the
  one formal analysis attempt, evidence gates, and round closure.
- **Stop condition**: any joint/global/future value enters a local estimator;
  the residual leaves the three-edge governor; holdout fitting occurs; source
  or parent closure is incomplete; or the engineering verification fails.

### TDD public seams

1. `R352 artifacts -> paired parent inventories`: accept only guarded zero and
   selected-local records with manifest-bound traces; reject the joint arm.
2. `causal endpoint histories -> one edge feature matrix`: a nonendpoint or
   future value cannot influence the edge estimator input.
3. `development cases/oracles -> frozen edge estimators -> holdout proposals`:
   holdout targets never enter fitting.
4. `formal rows -> pure gate decision`: distinguish eligible, no-training, and
   invalid without authorizing training in any branch.

### Execution status

- `HOLD`. This turn authorizes offline implementation and verification only.
  No rehearsal, seal, formal analysis, ANDES execution, or training occurs
  before the engineering return passes and the next Readiness gate is entered.

## Gate

The engineering return passes only when all four public seams are tested, the
adapter exposes no simulator/training command, parent/source closure is
complete, focused tests and preflight pass, and no R353 formal artifact exists.
Passing implementation does not authorize execution or strengthen CLM-0925.

## Asset protection contract

R341/R350/R351/R352 plans, questions, claims, code-bound sources, seals,
attempts, results, traces, manifests, feeds, verdicts, thresholds, and line
evidence remain byte-unchanged. Add only Q-0094, R353 plan, one probe, one
adapter, one artifact-independent public residual-headroom interface, focused
tests, and later separately authorized R353 evidence artifacts. No paper prose,
other manuscript line, neural code, or public remote is writable.

## Cross-references

- CLM-0925
- Q-0094
- R350 residual gate grammar and certified solver
- R352 matched neighbour-local parent
