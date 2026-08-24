# Corrected M/D revalidation experiment plan

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-24
- Verification Status: UNVERIFIED
- Version Label: corrected_md_revalidation_plan_v1
- Manuscript: `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`

## Decision

Do not rerun the whole research history. Rebuild only the manuscript-bearing
time-domain chain affected by the shared V4 M/D initialization/runtime-base
semantics. Preserve old artifacts as historical evidence; never pool them with
the corrected bank.

This document authorizes planning only. It authorizes no code change, ANDES
execution, training, retry, checkpoint reuse, or manuscript result update.

## Why revalidation is required

- `GENCLS.M` and `GENCLS.D` are base-converted power parameters in ANDES.
- V4 creates a 200-MVA device on a 100-MVA system base, then the controller
  writes runtime values directly.
- The current reset path records the unconverted M baseline as the interpolation
  anchor. A zero first action can therefore change runtime inertia while the
  reported action increment remains zero.
- The energy-port wrapper calls the same base-environment zero-M/D step. Its
  time-domain banks require revalidation too.
- This is an evidence-validity issue. It is not repaired by wording alone.

## Research questions

1. After one explicit device/system-base convention is enforced, does zero
   action preserve the initialized M/D state at reset and every control step?
2. Under a physically defended parameter card, do the deterministic direct-M/D
   and structured energy-port comparators retain their registered guards?
3. Does the direct-M/D learner trade-off survive the corrected physical object?
4. In an all-fresh factorial, are actor source, critic source, and their
   interactions with critic/reward conditions materially supported?
5. Are conclusions stable when arithmetic coordinates are replaced offline by
   inertia-weighted and nominal-modal sensitivity coordinates?

## Scope split

| Evidence object | Action | Reason |
|---|---|---|
| Direct-M/D deterministic banks | Rerun | Runtime M is affected; these banks define the comparator and feasibility boundary. |
| Projected SAC and RMS-penalty SAC | Retrain/evaluate | Policies were optimized on the affected object. |
| Eight-arm source factorial | Retrain all cells | Same object is affected; prior carryovers are aligned with actor-source N. |
| Energy-port unseen/parameter/topology banks | Rerun | The wrapper executes the affected zero-M/D base step. |
| Energy-port residual SAC | Conditional retrain | Required only if the manuscript retains the no-learning-increment claim. |
| DAE zero-authority identity | Recheck, not rediscover | Structural equilibrium result should be M/D-value independent; numerical realization must match the corrected card. |
| Physical M/D tensors and nonlinear finite ladder | Recompute targeted parts | Tensor values and time-domain ladder must use the corrected equilibrium/object. |
| Arithmetic/COI/modal coordinates | Offline reanalysis | Same accepted traces; no policy retraining is needed. |
| Invalid, aborted, superseded, tuning-only historical rounds | Do not rerun | They carry no final manuscript number after replacement evidence is available. |
| Rejected ICEMS source PDF/layout | Do not use as evidence | Visual/author reference only. |

## Fixed principles

- One scientific change at a time. Base correction, parameter-range choice,
  algorithm, reward, projector, disturbance bank, and statistical rule are not
  silently changed together.
- The final physical card is selected from model semantics and primary-source
  engineering justification, not from controller performance.
- Direct-M/D and energy-port estimators, references, and claims remain separate.
- Old and corrected numerical results are never averaged or presented as
  repetitions.
- Every formal training cell is fresh. No old checkpoint, optimizer state,
  replay buffer, curve, evaluation row, or training manifest enters the new
  confirmatory bank.
- Development probes and formal holdout artifacts have distinct identities.
- The primary seed is the inference unit; profiles are aggregated inside seed.

## Phase 0 — freeze the physical contract before code

### 0A. Base convention

Write one parameter card with distinct fields:

- device rating `S_n,i` and system base `S_b`;
- device-base `H_i`, `M_i=2H_i`, and `D_i`;
- runtime system-base M/D values;
- normalized-action-to-physical-action map;
- lower/upper clamps and slew rule;
- units and conversion equation for every field.

The formal implementation must convert exactly once. Reset values, interpolation
anchors, applied runtime values, observation/reward quantities, and telemetry
must use the declared convention.

### 0B. Parameter realism

Before any training, audit the source-paper definition and primary VSG
literature. Freeze:

- one final physically defended card used for all claim-bearing reruns;
- one Yang-benchmark card only if its numerical scale differs from the final
  card;
- a deterministic-only scale sensitivity between the two cards.

Do not train the full factorial on both cards by default. If deterministic
sensitivity reverses feasibility, endpoint ordering, or guard status, the
physical card becomes a declared experimental factor and the learning plan
must be re-frozen before training.

### 0C. Required invariants

The later code phase must test all of these before any simulator bank:

1. zero action: initialized runtime M/D equals first-step and later-step M/D;
2. telemetry: reported applied M/D equals ANDES readback;
3. round trip: device card -> system runtime -> device report is lossless;
4. heterogeneous card: all four device identities and weights are preserved;
5. nonzero action: both decoder branches, clamps, and slew have correct units;
6. energy port: zero M/D action cannot alter the slow parameter channel;
7. reset repeatability: repeated reset produces the same runtime card.

Any failure is engineering invalidity. No scientific run follows.

## Phase 1 — no-training physical revalidation

Run only after Phase 0 is frozen and implemented.

### 1A. Direct-M/D comparator

- Re-execute the registered zero action, nine-law bank, and the frozen
  development/evaluation schedule family under the corrected card.
- Keep disturbance profiles, selection split, window, endpoint definitions,
  and guards unchanged unless the plan records an explicit correction.
- Selection uses development profiles once. Evaluation profiles remain unseen.
- Report all failures; do not retune a law after evaluation visibility.

Gate: at least one frozen deterministic comparator must be finite and
guard-valid on its registered scope. Otherwise stop direct-M/D learner training
and revise the paper route.

### 1B. Structured energy port

- Re-execute the frozen unseen, extra-condition, and topology-variant banks.
- Keep the port law, gain, power/energy limits, topology list, and exclusion
  gates unchanged.
- Initialization/equilibrium failures are reported separately from performance.

Gate: if the frozen controller no longer passes its registered contract, drop
or redesign the constructive companion in a new plan; do not tune in this run.

### 1C. Trace bank for coordinate sensitivity

Retain complete frequency, runtime M/D, action, topology, and disturbance
traces for every valid record. These traces are the only input to Phase 2.

## Phase 2 — coordinate and local-math sensitivity

No policy training occurs in this phase.

### 2A. Common coordinate

For each accepted trace, compute in parallel:

- registered arithmetic common coordinate;
- fixed-baseline inertia-weighted COI coordinate;
- instantaneous-M-weighted coordinate as sensitivity only.

The fixed-baseline COI is the primary physical sensitivity. Instantaneous
weights are not silently substituted into the registered estimator.

### 2B. Differential coordinate

- Keep the registered two-area orthonormal differential basis.
- Derive a nominal small-signal modal/coherency basis from the corrected
  equilibrium before time-domain outcomes are inspected.
- Lock mode ordering, complex-pair handling, signs/phases, and projection rule.
- Report subspace angles, endpoint rank changes, and every pass/fail flip.

Gate: if the manuscript conclusion changes under COI or the matched nominal
modal subspace, the main text must report the sensitivity. Otherwise retain the
registered coordinates and state that they are structured, not modal.

### 2C. Local mathematics

- Recheck the folded first-order M/D channel at the corrected equilibrium.
- Recompute the physical M/D tensors at the corrected card.
- Rerun only the nonlinear finite ladder needed by the manuscript order claim.
- Preserve the distinction between an equilibrium structural zero, local
  tensors, and finite-window nonlinear evidence.

## Phase 3 — minimal learning ladder

Start only if Phases 1A and 2 pass their gates.

### 3A. Projected adapted SAC

Use the authentic-source arm of the final factorial as the projected-SAC
reference whenever its learner, reward, projector, bank, and seed contract are
identical. Do not train a duplicate R431-style bank merely to reproduce a table.

### 3B. RMS penalty

Train only the matched authentic-source RMS-penalty arm required for the
trade-off claim. Match the final-factorial seeds and profiles. Freeze the
penalty formula and coefficient before training. Do not reopen coefficient
selection after result visibility.

### 3C. Historical value-normalization row

Do not rerun it by default. Remove that numerical row from the manuscript if it
cannot be represented by a current corrected arm. Historical route narration
does not justify a separate high-cost bank.

### 3D. Energy-port residual learner

This is secondary. Retrain the matched message/no-message residual arms only if
the paper retains the statement that learning adds no endpoint or message
increment. Otherwise retain only the corrected deterministic energy-port result.

## Phase 4 — all-fresh source factorial

### Design

- Factors: actor source `{N,P}` x critic source `{N,P}` x reward access `{0,1}`.
- `N`: authentic same-time ring-neighbour source.
- `P`: fixed-point-free same-time row permutation of the authentic source pool.
- Training budget: 43,200 interaction steps per cell, unchanged.
- Checkpoints: half and final; final is primary, half is diagnostic only.
- Seeds: new identities not used in the exploratory R477 analysis.
- Base states: newly generated and matched across all eight arms per seed.
- Carryover: zero old training cells; within-round shared immutable inputs are
  allowed only after hash and identity checks.

Before training, routing must prove per time/slot/scenario:

1. the N and P source multisets are identical;
2. every P tuple differs from the recipient's authentic tuple;
3. no P donor is a true neighbour of its recipient;
4. both replicas read the same contemporaneous state pool;
5. only the registered factor columns change.

Any failure classifies the factorial as design-invalid and stops training.

### Estimands

Let `L` be final-checkpoint disturbance differential energy; lower is better.
Positive source effects favour authentic source:

- actor main effect: mean `log[L(P,c,r)/L(N,c,r)]`;
- critic main effect: mean `log[L(a,P,r)/L(a,N,r)]`;
- actor x critic interaction: actor effect at `c=N` minus actor effect at `c=P`;
- critic x reward interaction: critic effect at `r=1` minus critic effect at `r=0`.

Average matched profiles and nuisance-factor levels inside seed. The across-seed
mean is the estimand.

### Materiality and multiplicity

- Materiality boundary for every ratio or ratio-of-ratios: `log(1.10)`.
- Test the materiality null directly; a zero-null test is insufficient.
- Use seed-level exact sign-flip/randomization inference.
- Apply Holm control to the four claim-bearing tests as one family.
- Bootstrap intervals and leave-one-seed-out estimates are descriptive only.
- Directional interaction hypotheses are frozen from the old descriptive bank;
  old observations are used for design/power only, never pooled with outcomes.

### Sample size

Do not reuse `n=6`. Before code is sealed, create a prospective power artifact.
Choose the smallest `n_star` that simultaneously:

1. satisfies the exact-sign-flip resolution required by four-test Holm control;
2. provides at least 80% power for a true 20% main effect above the 10% bar;
3. provides at least 80% power for each registered interaction alternative;
4. uses the conservative upper variance bound from the old seed-level effects;
5. fits the measured wall-clock and artifact budget.

Until this artifact exists, `n_star` remains unresolved and formal training is
not run-ready. Expected factorial workload is `8 * n_star` fresh training cells
plus 16 arm-stage evaluation jobs.

### Formal outcomes

- `MATERIAL-MAIN-EFFECT`: at least one main-effect materiality null rejected.
- `MATERIAL-INTERACTION`: at least one interaction materiality null rejected.
- `MATERIAL-EFFECT-NOT-ESTABLISHED`: validity complete, no registered rejection.
- `DESIGN-INVALID`, `EXECUTION-INCOMPLETE`, or `INTEGRITY-INVALID`: no effect
  verdict; numerical effects stay out of claims.

Absence of rejection is never written as zero effect or equivalence.

## Formal validity and stop rules

### Engineering invalidity

Stop on unit/readback mismatch, zero-action drift, TDS failure beyond the frozen
validity rule, nonfinite learner state, wrong source routing, hash mismatch,
missing manifest/sidecar, output collision, or resource-safety guard.

### Scientific stop

- Phase 1 comparator failure stops dependent learning.
- Phase 1 energy-port failure stops the companion branch only.
- Phase 2 conclusion flip forces manuscript/estimand review before training.
- A formal factorial has no outcome-based early stop.

### Retry

No silent retry. Preserve every failed attempt. Any post-seal source or contract
change requires a successor round and a new seal.

## Efficiency plan

- Cheapest order: unit invariants -> deterministic banks -> offline coordinate
  and math sensitivity -> minimal learner arms -> full factorial -> optional
  energy-port residual learner.
- Existing capacity evidence supports 16 workers plus one launcher with one
  native numerical thread per process for the prior matching workload. This is
  a measured derived budget, not a permanent hard cap.
- Before a corrected formal seal, confirm that host, job shape, memory reserve,
  other running work, and output rate remain compatible. Otherwise run a
  representative capacity measurement first.
- For `J` jobs and frozen concurrency `c`, estimate
  `waves=ceil(J/c)` and `ETA=setup + waves*[t_low,t_high] + finalization` from
  the corrected rehearsal/first permitted wave. Do not invent an ETA now.
- Formal progress monitoring reads only process count, valid completed-job
  count, terminal artifacts, resource telemetry, and engineering failures.
  Intermediate scientific outcomes remain blind.

## Manuscript replacement rule

After all required successor evidence closes:

- replace affected old numbers, figures, tables, and claims; do not append a
  second result series;
- mark old claims superseded or historical as required by the ledger;
- regenerate both manuscript figures from corrected artifacts;
- report coordinate sensitivity and the physical parameter card explicitly;
- keep the fixed title unchanged unless the corrected evidence fails one of its
  term-level support gates;
- run evidence, domain, pre-submission, and PDF layout audits again.

## Explicit non-goals

- no new algorithm family;
- no hyperparameter sweep;
- no full replay of every failed historical repair;
- no full factorial at multiple M/D scales unless Phase 1 proves scale is a
  material scientific factor;
- no probability, safety, EMT, HIL, or topology-general claim;
- no experiment or code change in this planning turn.

## Unresolved inputs before implementation

1. Final device/system-base parameter card and primary-source justification.
2. Whether the Yang benchmark card differs from the final physical card.
3. Prospective `n_star` and interaction alternatives/power artifact.
4. Corrected-job runtime, memory, disk growth, and final artifact budget.
5. Whether the manuscript retains the energy-port residual-learning claim.
6. Exact successor-round partition and formal entry commands.

## Experiment efficiency card

- Execution readiness: HOLD
- Decision and authority: owner authorized planning; owner explicitly forbids experiment/code in this turn.
- Stage and scientific contract source: prospective revalidation program; formal contracts not yet sealed.
- Run state: pre-code, pre-seal.
- Cheapest decisive work and escalation gate: resolve Phase 0 card, then implement/test invariants; no simulator work before pass.
- Completion, stop, retry, and interruption rules: frozen above.
- Jobs and dependencies: symbolic until `n_star` and optional energy-port learner disposition are frozen.
- Resource evidence: prior matching workload measured 16 workers plus one launcher; compatibility recheck required.
- Unresolved inputs: six items listed above; next owner is the later implementation/planning turn.
- Plumbing check: not performed or authorized.
- Capacity evidence: inherited evidence only; not yet bound to corrected source.
- Concurrency and bottleneck: unresolved at formal seal; tentative measured budget is not a hard cap.
- ETA: intentionally unset until corrected representative timing exists.
- Progress signals: defined above; no monitor is active.
- Authorized action: store and review this plan only.
