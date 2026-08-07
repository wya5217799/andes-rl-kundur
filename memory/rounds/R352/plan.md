---
round: R352
state: completed
manuscript_line: decoupling-marl-model-first
opened: '2026-08-07'
closed: '2026-08-07'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R352 plan - neighbour-distributed deterministic closed-loop gate

**Opened**: 2026-08-07
**Driver**: Tune and test a real endpoint-neighbour deterministic controller
through the exact three-edge action and physical limits reserved for a future
multi-agent policy.
**Parent**: CLM-0920; Q-0093; R344 joint-information upper reference

## TL;DR

Use exposed R344 disturbance cases only to choose two shared local gains, then
freeze them before a new disturbance-shape holdout. Compare the selected local
controller with zero edge action under an identical plant, action, governor,
limits, timing, and metrics. Execute a same-action joint-information arm only
as a qualified upper reference. No branch trains a network.

## Snapshot at plan-time (oracle as of 2026-08-07)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete; re-render STATE.md to refresh current state, but keep this -->
<!-- block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) - verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0092 closed-positive @ R351, by CLM-0920 - Can one deterministic three-edge controller execute from endpoint-only neighbour information through the future policy's exact physical governor?
- Q-0091 closed-negative @ R350, by CLM-0915 - Does the frozen deterministic bridge leave material, observable, and physically usable residual headroom before neural training?
- Q-0090 closed-positive @ R344, by CLM-0910 - Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?

## Methodology

**Lane**: evidence. R352 creates new nonlinear trajectories, freezes a
development/holdout split, and may change the residual-headroom decision. All
offline implementation belongs to this round; no holdout command is allowed
before development selection, preflight, representative capacity evidence,
same-path rehearsal, and a create-only formal seal.

### Research Supervisor route and comparison gate

- **Decision**: `QUALIFY` for the complete three-arm design; `ALLOW` for the
  primary bounded comparison of the selected local controller against zero
  edge action.
- **Executed objects**: zero three-edge action; one shared-gain endpoint-local
  linear controller; one same-gain joint-information linear upper reference.
- **Identified estimand**: paired effect of this selected local deterministic
  controller over zero edge coordination on the untouched finite bank.
- **Required qualification**: the joint-information arm changes information
  ownership and the action mapping, so it is an upper reference rather than a
  pure information-value estimate. Both linear laws are single constrained
  instances, not controller-family representatives.
- **Stay-out claims**: no class-level distributed-control, optimal-control,
  multi-agent, neural, topology, stability, safety, robustness, deployment,
  or title-term validation.

### Handoff: Research Supervisor to Ask Matt

- **Current owner**: Ask Matt's test-first implementation route.
- **Required input**: CLM-0920, Q-0093, the R351 public edge/governor seam,
  the existing R344 physical plant/readback utilities, and this frozen design.
- **Acceptance check**: closed-loop actions are computed from the declared
  information, all three arms traverse the same three-edge governor, and the
  runner cannot inspect holdout outcomes before the seal.
- **Authority and write scope**: Q-0093/R352; one reusable joint reference if
  needed, one R352 runner, public-seam tests, and R352 evidence artifacts. Do
  not modify R341/R344/R350/R351 sealed assets or any other manuscript line.
- **Return artifact**: tested implementation plus create-only development and
  formal entrypoints.
- **Return verification**: targeted tests and `round_preflight.py R352`.
- **Next owner**: Model-first research owner for capacity, seal, execution,
  evidence audit, claim, verdict, and line reconciliation.
- **Stop condition**: any global value enters a local actor; the action has
  other than three edge coordinates; an arm bypasses the matched governor; or
  tests/rehearsal/preflight fail.

### Test-first public seams

1. `LocalEdgeObservation -> one normalized action`: only the two edge
   endpoints and that edge's previous flow are representable.
2. `three local actors -> ordered three-vector`: changing a non-endpoint node
   cannot influence the unrelated edge actor.
3. `joint endpoint set -> ordered three-vector`: the central diagnostic is
   explicitly labelled joint-information but uses the same two gains and
   returns the same action coordinates.
4. `three-vector -> matched governor -> four node requests`: every arm shares
   incidence, edge amplitude/slew, endpoint headroom, power/ramp/energy/SOC
   limits, and physical readback.
5. `development records -> one selection`: selection uses only registered
   development records, is deterministic, and cannot accept a holdout record.

### Frozen controller and comparison contract

- Action edges and orientation: `(0,1)`, `(1,2)`, `(2,3)`; normalized action
  dimension three; source-positive convention from R351.
- Local law per edge: negative shared-gain feedback on endpoint frequency and
  RoCoF differences. The three actors execute independently.
- Candidate gains: frequency-difference gain `{50, 200, 500}` per Hz crossed
  with RoCoF-difference gain `{0, 25, 100}` seconds per Hz. The grid is fixed
  from already exposed R344 zero-arm maxima of about `0.00204` Hz adjacent
  frequency difference and `0.00431` Hz/s adjacent RoCoF difference; it is not
  changed after new R352 trajectories.
- Joint upper law: remove the joint mean from all four node measurements and
  solve the fixed tree incidence for three normalized edge actions. It reuses
  the selected local gains and receives no additional tuning budget.
- All arms use zero common/base request, edge flow limit `0.05` system pu,
  edge slew limit `0.05` system pu per `0.2` second interval, the R351/R344
  physical projector, and the same BESS readbacks and guards.

### Development and untouched banks

- **Development identity**: the sixteen exposed R344 low-amplitude ramp-hold
  cases: `FV0` and `FV1`, four registered load channels, and both signs.
  Execute zero plus all nine local candidates. After selection, execute the
  selected-gain joint diagnostic only on this exposed bank.
- **Selection rule**: reject any candidate with an incomplete record, failed
  locality/action/physical guard, controller non-engagement, requested fleet
  imbalance above `1e-12` system pu, or common-coordinate ratio above `1.05`
  in any case. Among survivors, minimize the geometric mean paired ratio of
  differential-coordinate energy to zero; break exact ties by lower frequency
  gain, then lower RoCoF gain. If none survives, close valid-negative without
  creating or viewing the holdout.
- **Holdout identity**: sixteen previously unexecuted low-amplitude
  `staggered-rise` cases on the same two qualified points, four load channels,
  and both signs. Its fixed unit profile is
  `(0.20, 0.60, 1.00, 0.70, 0.35, 0.10)` and uses the R344 per-channel low
  amplitudes. The formal arms are zero, selected local, and same-gain joint
  upper: forty-eight trajectories.
- The holdout points are not new operating points. The claim ceiling is an
  untouched disturbance-shape bank on two exposed points.

### Endpoints and thresholds

- Primary endpoint: paired `differential_coordinate_energy` ratio, local over
  zero, with the scenario as the unit of analysis.
- Guard endpoint: paired `common_coordinate_iae` ratio, local over zero.
- Physical diagnostics: maximum pairwise frequency difference, requested and
  achieved node powers, controller engagement, requested fleet imbalance,
  SOC, voltage, limiter, ramp, timing, event, solver, and DAE guards.
- Reuse R344's prospective materiality and worst-case values: paired mean
  differential improvement at least `0.02`; maximum single-scenario
  differential and common worsening no more than `0.05`.
- The joint arm is reported descriptively with paired ratios. It neither
  changes the local pass/fail result nor authorizes training.

### Execution staging and efficiency gate

- **Current readiness**: `RUN-READY` for the one sealed formal attempt. The
  reviewed successor development chain selected `kf500_kr0` without inspecting
  holdout records; all 160 grid records and 16 joint diagnostic records passed
  their registered execution guards. The no-trajectory formal rehearsal passed
  and seal `35afdf4f2120feaf4db0c909f1b18669795b8f5338dbe26b611499d488282021`
  binds the contract, selected controller, full local source closure, installed
  simulator identity, capacity record, launch budget, and 48 formal specs.
- Cheapest work: unit tests, no-trajectory rehearsal, then representative
  closed-loop capacity rungs. Development follows only after one safe process
  budget is measured. Formal follows only after deterministic selection and a
  second rehearsal verifies that the formal output is absent.
- Capacity evidence: the R352 ladder measured whole-host process rungs 2, 4,
  and 8 on representative 25-step closed-loop trajectories. All rungs passed;
  their throughputs were approximately 0.435, 1.134, and 1.957 trajectories
  per second. The highest measured valid rung, 8, is frozen for development
  and formal execution. Each process has one native numerical-library thread.
  The host exposed 32 logical processors, about 18.26 GB available memory
  remained after the selected rung, swap use was zero, repository-volume free
  space exceeded 745 GB, and other reserved research processes were zero.
  Development ETA is about 1.5-2.5 minutes for 176 total trajectories including
  the selected joint diagnostic; formal ETA is about 0.5-1 minute for 48
  trajectories. Use terminal-only observation with a five-minute hard
  envelope. No R351 budget is inherited.
- **Engineering recovery**: the first R352 development attempt and its
  capacity record are preserved unchanged. Post-implementation review found
  that the formal paired mean used a ratio of aggregate means, the diagnostic
  arm could affect the primary gate, the seal omitted transitive execution
  sources and installed-simulator revalidation, and formal arms were not
  staged. No holdout trajectory had been executed or inspected. Those defects
  invalidate the first attempt as source evidence. The successor uses `v2`
  create-only development/capacity/result paths, the identical candidate grid,
  banks, thresholds, and selection rule, and receives no outcome-driven tuning.
  Its capacity record replaces the numerical budget above for formal launch;
  the preserved first attempt remains engineering history only.
- **Successor capacity**: the reviewed source closure repeated process rungs
  2, 4, and 8 at approximately 0.322, 1.129, and 1.905 trajectories per
  second. All rungs passed, so 8 whole-host Python processes with one native
  numerical thread each are frozen for formal execution. At the selected rung
  about 18.26 GB memory remained available, swap use was zero, repository
  volume free space was about 744.88 GB, and no other research Python process
  was present. The 48-trajectory staged formal bank has an operational ETA of
  roughly 25-60 seconds and retains the five-minute hard envelope.
- **Formal launch card**: scope is one create-only staged attempt with 48
  trajectories maximum; capacity is 8 whole-host Python processes, one native
  thread each, zero peer reservations; ETA is 25-60 seconds with a five-minute
  hard envelope; monitoring is terminal-only; completion is all three 16-case
  arms, while the zero or local stage stops immediately on a registered
  integrity or physical failure. The joint stage is diagnostic and cannot
  change the local gate. All outputs and failures are retained; retry and
  training remain unauthorized.
- Engineering invalidity stops on crash, source drift, missing/duplicate
  inventory, non-finite telemetry, failed process guard, output collision, or
  physical/information/action guard failure. No retry exists inside the sealed
  formal attempt.
- Development is tunable only by the registered selection rule. Formal is
  frozen and terminal after all forty-eight records or the first invalid
  staged stop.

### Prospective outcomes

- `DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS`: complete paired inventory; every
  structural and physical guard; paired mean differential improvement at
  least 2%; no differential or common case worse by more than 5%. Close Q-0093
  positive and authorize only a separately registered residual-headroom
  question.
- `DISTRIBUTED-DETERMINISTIC-NO-HOLDOUT-VALUE`: valid complete execution but
  the local arm misses one or more performance thresholds. Close Q-0093
  negative; training remains blocked.
- `NO-DEVELOPMENT-CANDIDATE`: no candidate survives the prospective
  development rule. Close Q-0093 negative without holdout execution.
- `DISTRIBUTED-DETERMINISTIC-PHYSICAL-GUARD-FAIL`: intact comparison contract
  but a physical guard fails. Preserve artifacts and stop.
- `INVALID-DISTRIBUTED-DETERMINISTIC-EXECUTION`: source, seal, inventory,
  information, action, process, or telemetry integrity fails. Preserve the
  attempt and do not interpret performance.

## Gate

The local deterministic baseline qualifies only if the create-only sealed
holdout returns `DISTRIBUTED-DETERMINISTIC-HOLDOUT-PASS`. Development success,
the joint upper reference, or passing code tests cannot substitute for this
gate. No R352 outcome authorizes neural training.

## Asset protection contract

R341/R344/R350/R351 plans, questions, claims, sources, seals, attempts,
traces, results, thresholds, feeds, and verdicts remain byte-unchanged. Add
only Q-0093, R352 implementation/tests/runner, prospective capacity and seal
artifacts, create-only R352 results, and, after a terminal valid result, the
R352 feed, claim, verdict, manifest registration, and selected-line navigation
refresh. No other paper line and no public remote are writable.

## Cross-references

- CLM-0920
- Q-0093
- R344 diagnostic joint-information upper reference
