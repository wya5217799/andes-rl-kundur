# Corrected M/D revalidation experiment plan

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-24
- Verification Status: OFFLINE-IMPLEMENTED / PHYSICAL-HOLD
- Version Label: corrected_md_revalidation_plan_v2_preseal_repair
- Manuscript: `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`

## Decision

Do not rerun the whole research history. Rebuild only the manuscript-bearing
time-domain chain affected by the shared V4 M/D initialization/runtime-base
semantics. Preserve old artifacts as historical evidence; never pool them with
the corrected bank.

The 2026-08-24 corrective turn authorizes Phase-0 code, tests, and prospective
design-contract repair. It still authorizes no ANDES execution, training,
formal attempt, checkpoint reuse, or manuscript result-number update.

Capacity and rehearsal files created before the invariant gate and final code
review are quarantined as non-authoritative. They use the old authority
generation, cannot enter a seal, and are never used as scientific evidence.

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
2. Under the frozen project-calibration parameter card, do the deterministic direct-M/D
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

## Conclusion dependency and fast validation order

The 224-job factorial is a shelf plan, not the next execution queue. A lower
gate can make every downstream job unnecessary, so work advances one
falsifiable conclusion at a time:

1. **Semantic invariant (next, engineering-only):** the owner's current
   instruction authorizes only zero-family capacity measurement and rehearsal.
   After recording that bounded authorization, run the two registered zero-action disturbances,
   one bounded nonzero five-substep M/D readback trajectory, and reset
   repeatability. Run serially and make no paper claim. Any target/readback,
   unit, reset, or TDS failure stops the route and keeps every old corrected-
   object conclusion unverified.
2. **Deterministic canary:** only after Step 1 passes, run the two canaries
   below in order. Each uses an already registered estimator and threshold;
   no new single-trajectory surrogate metric is invented. Both are route
   triage, not formal evidence, and neither authorizes training.

   - **2A, direct-M/D first:** run exactly 12 trajectories: arms `zero` and
     `local_neighbour_md_km2_kd2` on profile `dev_a`, using the complete paired
     scenario set `dev_a_{common,differential,localized}_{positive,negative}`.
     Use the existing profile summarizer and the dedicated 12-record canary
     classifier. A canary pass requires valid complete summaries, positive
     zero references, no mapping/bound/slew failure, action saturation at most
     0.05, nonconstant action variation above `1e-6`, per-VSG action dispersion
     above `1e-6`, every common-frequency/peak/RoCoF no-harm guard relative to
     `zero` at the registered 3% ceiling, and both the off-diagonal and
     disturbance-differential ratios to zero at most 0.95. The formal
     evaluation action-RMS/action-variation no-harm checks are not used here:
     their reference is the selected deterministic comparator itself, so they
     would be circular in this zero-versus-comparator transport canary.
     Failure flags the old direct-M/D comparator conclusion as potentially
     changed and opens only the direct-M/D formal bank.
   - **2B, energy port only if 2A passes:** run exactly 20 trajectories: arms
     `local_feasibility_native` and `bandpass_k3p5` on the frozen evaluation
     condition `eval3_probe_pq0_minus_0p40` for modes `common`, `inter_area`,
     `local_area_1`, and `local_area_2`, each at both signs, plus disturbances
     `eval3_disturbance_pq0_plus_0p60` and
     `eval3_disturbance_bus15_plus_0p55`. Use the existing held-out summarizer.
     A canary pass requires all registered guards, differential ratio at most
     0.95, and probe cross-ratio at most 1.10. Failure flags only the paper's
     bounded positive energy-port claim as potentially changed and opens only
     that deterministic bank.

   Routing is fixed before results: if 2A fails, stop before 2B; if 2A passes
   and 2B fails, open only the energy-port bank; if both pass, neither old
   conclusion is treated as revalidated and the direct-M/D formal bank remains
   first because it carries the manuscript's main negative claim. A canary
   pass is never migration evidence and never justifies copying an old number.
3. **One branch at a time:** formally revalidate the smallest affected
   deterministic bank. Stop if its old conclusion changes. Open a learning
   canary only if the corrected deterministic conclusion survives and the
   manuscript still needs that learning claim.
4. **Factorial last:** fresh source-factor training remains deferred until all
   upstream gates survive. Its registered power plan preserves the option; it
   does not authorize or schedule 224 jobs.

Past results remain historically valid only for the old implemented object.
They are not silently relabelled as evidence for the corrected object.

Parallelism is used only among unique jobs inside the currently open gate, at
the measured safe worker count. Downstream gates are never launched
speculatively. After every completed gate, write a create-only report containing
the frozen input/output hashes, validity result, registered metrics, whether the
corresponding old Yang-line conclusion remains plausible or has changed, the
decision `retain old route` or `redesign successor`, and exactly one next gate.

## Fixed principles

- One scientific change at a time. Base correction, parameter-range choice,
  algorithm, reward, projector, disturbance bank, and statistical rule are not
  silently changed together.
- The current card is an inherited project calibration held fixed to isolate
  the conversion correction. It is not called a strict Yang physical card and
  is not selected from controller performance.
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

### 0B. Parameter scope and provenance

The Yang paper supplies action increments but not baseline `H0/D0` or enough
unit/base information to reconstruct a unique physical card. The registered
`H0=100 s`, `M0=200 s`, `D0=100` values are therefore explicitly an inherited
project calibration, not a Yang benchmark. The justification note records this
boundary and confirms that no corrected-bank outcome selected the values.

All Phase-1 conclusions are limited to this corrected project-calibration
finite bank. A strict Yang physical benchmark or a second scale is a new
prospective factor requiring a separately sourced card and a re-frozen plan.

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
- Selection uses development profiles once and writes exactly one winner using
  the frozen priority branches and smallest-global-index tie break.
- Report all failures; do not retune a law after evaluation visibility.

Gate: only that development-selected winner is tested on evaluation profiles.
It must be finite and guard-valid on all four registered evaluation profiles;
one-to-three passing profiles cannot open the gate. If it fails, there is no
fallback to another evaluation-visible comparator: stop
direct-M/D learner training and revise the paper route.

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
Phase 3 specifies this reference but does not execute it first. The arm is owned
by the single frozen Phase-4 batch, trained once there, and consumed by the
Phase-3 comparison only after that batch completes. Its batch identity and
hashes are shared; outcome-driven reuse or duplicate training is forbidden.

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

For each seed, first compute every profile-specific log ratio, then average
profiles with equal weight and nuisance-factor levels with equal weight exactly
as written above. The across-seed mean is the estimand. Any missing, duplicate,
nonfinite, or nonpositive matched cell invalidates the whole seed and classifies
execution as incomplete; available-case averaging is forbidden.

### Materiality and multiplicity

- Materiality boundary for every ratio or ratio-of-ratios: `log(1.10)`.
- Familywise alpha is `0.05`; all four hypotheses are one-sided in the frozen
  favourable direction.
- Test each boundary null directly with the exact one-sided Wilcoxon signed-rank
  distribution of the boundary-centred seed effects; a zero-null test is
  insufficient.
- The exact test requires independent seeds and a continuous symmetric
  location-shift distribution. A zero difference or tied absolute rank makes
  the inferential verdict invalid rather than triggering an asymptotic fallback.
- Apply Holm step-down control to the four raw materiality p-values as one
  family and retain raw p, adjusted p, threshold, and decision for every test.
- Bootstrap intervals and leave-one-seed-out estimates are descriptive only.
- Directional interaction hypotheses are frozen from the old descriptive bank;
  old observations are used for design/power only, never pooled with outcomes.

### Sample size

The prospective power artifact freezes `n_star=26` new training seeds
`501..526` and the four profiles `canary_eval_a..canary_eval_d`. It uses
the old six-seed final-checkpoint bank only to estimate variance and interaction
direction, never as outcomes. Planning alternatives are 20% for both main
effects, 30% for actor-by-critic, and 25% for critic-by-reward, each tested above
the 10% boundary. The variance bound is the larger old sample standard deviation
within the main-effect pair or interaction pair.

Power is simulated under an independent normal location-shift planning model
with 200,000 deterministic draws per candidate size using
the exact signed-rank rejection region at `0.05/4=0.0125`, the worst first Holm
threshold. The 95% Wilson lower power bound exceeds 0.80 for all four tests at
26 seeds; the limiting critic-by-reward value is about 0.817. The artifact and
reproducible implementation are registered in the active round.

If its upstream gates ever open, the frozen factorial workload is 208 fresh training cells plus 16 arm-stage
evaluation jobs, 224 unique jobs total. This statistical freeze does not make
the run executable: measured final-source capacity, time, memory, disk, and
artifact budgets still gate launch.

### Formal outcomes

- `MATERIAL-MAIN-EFFECT`: at least one main-effect materiality null rejected.
- `MATERIAL-INTERACTION`: at least one interaction materiality null rejected.
- `MATERIAL-EFFECT-NOT-ESTABLISHED`: validity complete, no registered rejection.
- `DESIGN-INVALID`, `EXECUTION-INCOMPLETE`, or `INTEGRITY-INVALID`: no effect
  verdict; numerical effects stay out of claims.

Absence of rejection is never written as zero effect or equivalence.

These contrasts estimate total algorithm effects for the fixed learner,
projector, budget, environment, profiles, and seed population. Without an
optimization-gap control they do not identify the intrinsic value of neighbour
information or a population optimum.

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
- Prior capacity evidence is historical only. The pre-review files produced in
  this round are quarantined because the sources and authority generation
  changed; none can bind the future seal.
- Before a corrected formal seal, confirm that host, job shape, memory reserve,
  other running work, and output rate remain compatible. Otherwise run a
  representative 1/2/4/8/12/16-worker capacity ladder with at least 32 jobs per
  rung; gains in the 3%-7% boundary band are measured twice and averaged.
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
- no ANDES execution, training, formal attempt, or manuscript result-number
  change in the current repair turn.

## Remaining launch inputs

1. A create-only hashed physical-execution authorization bound to the exact
   runner, plan, parameter card, family, and permitted pre-formal command.
2. Corrected regression baselines and real-ANDES invariant results after that
   explicit authorization.
3. Corrected-job capacity, runtime, memory, disk growth, and artifact budget.
4. Whether the manuscript retains the energy-port residual-learning claim.
5. Final source map, dual review, formal seals, and explicit owner approval.

## Experiment efficiency card

- Execution readiness: HOLD
- Decision and authority: owner authorized code/design repair but forbids ANDES, training, and formal execution.
- Stage and scientific contract source: Phase-0 implementation repaired; formal contracts not sealed.
- Run state: offline implementation complete, physical validation pending, pre-seal.
- Cheapest decisive work and escalation gate: finish offline review, then request explicit permission for corrected baseline/invariant execution.
- Completion, stop, retry, and interruption rules: frozen above.
- Jobs and dependencies: only the small semantic invariant is next; the 224-job factorial is frozen as a shelf plan and remains deferred.
- Resource evidence: historical only; compatibility remeasurement is required on final sources.
- Unresolved inputs: five launch gates listed above.
- Plumbing check: offline only; physical plumbing is not authorized.
- Capacity evidence: no current authoritative evidence; old-generation files are quarantined.
- Concurrency and bottleneck: unresolved at formal seal; tentative measured budget is not a hard cap.
- ETA: intentionally unset until corrected representative timing exists.
- Progress signals: defined above; no monitor is active.
- Authorized action: code/design repair and offline review only.

## 2026-08-25 diagnostic visibility audit

The repair3 authorization covered only the zero-family capacity ladder and
semantic rehearsal. Later direct-M/D and energy-port runs are preserved as
unauthorized scratch diagnostics, not gate evidence. In particular,
`eval_a`--`eval_d` have now been viewed and permanently lose unseen-holdout
status. They cannot appear in a future formal evaluation bank.

Accordingly, the pre-registered route above has not been formally superseded.
A direct-canary pass followed by a diagnostic energy-canary failure still
leaves the deterministic energy-port bank as the official next gate. The
recommended alternative is an explicit successor decision to abandon the
energy-port positive claim, prospectively register genuinely fresh direct-M/D
holdouts, and then issue a new hash-bound physical authorization. Until one of
those paths is owner-approved, no formal bank or training phase is open.
