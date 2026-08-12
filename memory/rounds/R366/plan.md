---
round: R366
state: completed
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R366 plan — unit-valid direct-M/D comparator design gate

**Opened**: 2026-08-12
**Driver**: Convert the R365 object-gate PASS into a permission-matched,
unit-valid deterministic-comparator contract before any controller run or
neural training.
**Parent**: Q-0102; CLM-0975; R365

## TL;DR

Workload: `evidence` because this round freezes the comparator and learning
inference ceiling.  Add and test a pure 60-Hz observation adapter plus one
four-agent local-neighbour M/D controller family.  PASS authorizes only a
separate non-learning deterministic efficacy/headroom experiment; no ANDES
execution or training occurs in R366.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?
- Q-0100 closed-positive @ R363, by CLM-0965 — On the exposed development bank, does adding a common residual-power channel to the three-edge zero-common action basis enlarge the per-case physical action-space headroom, showing that the zero-common residual contract itself (rather than information) limits the R358 feasibility?
- Q-0099 closed-negative @ R362, by CLM-0960 — On the exposed development bank, does replacing the one-hop neighbour snapshot messages with frozen R341-model causal prediction trajectories (DMPC-style shared prediction) let a pre-registered tuning-free non-neural map family recover both registered endpoint gates, showing learnable structure that R359, R360, and R361 could not reach from endpoint-only or snapshot-message information?

## Methodology

### Research Supervisor design gate

- **Decision question**: can the next comparison identify controller and later
  message-enabled MARL value on the same four-VSG object without frequency-unit,
  information, action-space, or actuator-identity confounding?
- **Scientific object**: the four R365-verified GENCLS VSG parameter objects,
  ordered as actors `0..3` at buses `(12,16,14,15)`.
- **Inference ceiling**: electromechanical parameter-seam coordination on one
  modified-Kundur ANDES plant.  Storage energy, converter current, thermal
  limits, EMT behavior, hardware feasibility, safety, and topology
  generalization remain outside scope.
- **Comparison-identifiability target**: `ALLOW` only for a later bounded
  comparison in which all arms use the exact contract below.  Existing DAPI,
  relative-RoCoF, edge-action, common-scalar, and storage-power controllers are
  implementation references only and are not eligible comparator arms.

### Frozen 60-Hz observation contract

- The ANDES plant remains physically 60 Hz.  The protected V4 environment is
  unchanged; a new adapter converts its legacy 50-Hz frequency and RoCoF slots
  by the exact ratio `60/50` before either deterministic control or learning.
- Base observation layout remains seven fields per actor: own active power,
  own frequency deviation, own RoCoF, two neighbour frequency deviations, and
  two neighbour RoCoFs.  The adapter leaves power unchanged and scales exactly
  slots `1..6`; it rejects non-finite values, wrong shapes, nonpositive bases,
  or a physical base other than 60 Hz for this line.
- Communication graph is the R365 undirected ring.  Zero delay and zero
  dropout are the first comparator condition.  Delay/dropout are held-out
  stressors, not tuning inputs.
- Physical reporting uses only `freq_hz_physical` and the simulator 60-Hz base.
  The legacy V4 reward and 50-Hz-labelled `freq_hz` are not objectives or
  paper endpoints for this line.

### Frozen actuator and timing contract

- Each actor independently emits normalized `(a_M, a_D)` in `[-1,1]^2`; the
  existing zero-centred V4 decoder maps these to its own GENCLS M/D parameters.
- Reuse R365 limits: baseline `M=200`, `D=100`; decoder ranges
  `delta-M in [-200,600]`, `delta-D in [-200,600]`; executed lower clamps
  `M>=20`, `D>=10` in model units.
- Add one permission-matched normalized per-decision slew limit of `0.25` on
  each action coordinate.  All later controller and learner arms start at zero
  action, use the same 0.2-s update rate, and pass through the same clip/slew
  path.
- This is bounded parameter modulation, not storage-power or hardware
  actuation.  No storage state, energy budget, current limit, or achieved
  converter command is silently introduced into one arm.

### Deterministic baseline family

- Name: `local-neighbour adaptive M/D`.
- Runtime architecture: four independently stateful local agents.  Each agent
  receives exactly one adapted seven-field row and returns exactly its own
  two-coordinate action.  The harness routes rows but computes no global
  statistic and performs no scalar or edge-action aggregation.
- Inertia action is an odd, bounded response to own transient severity minus
  mean neighbour severity.  Damping action is a nonnegative bounded response
  to own absolute frequency deviation plus mean relative frequency and RoCoF.
  Both targets pass the common clip/slew path.
- Severity uses only adapted own/neighbor frequency and RoCoF fields; active
  power remains observed but is excluded from this baseline law so a nonzero
  pre-disturbance power setpoint is not misread as transient severity.
- Freeze the nine-candidate gain grid
  `inertia_gain x damping_gain = {0.5,1.0,2.0} x {0.5,1.0,2.0}`.
  Development selection minimizes differential-frequency energy, then
  differential-power energy, with common-frequency harm, action variation,
  saturation, bounds, failure, and provenance as hard guards.  One selected
  instance becomes the sole strong deterministic comparator before holdout.

### Direct-MARL falsifiable question and stop rules

- Later question: under the exact matched contract, does message-enabled
  direct per-VSG M/D MARL reduce paired differential-frequency energy by at
  least 5% relative to the selected deterministic controller, with a 95%
  paired interval excluding no improvement, while causing no more failures
  and no greater than 5% harm in common-frequency error or control variation?
- Before any training, the selected deterministic controller must improve
  mean differential-frequency energy by at least 10% versus zero action on a
  development bank, with no extra failure and no greater than 5% harm in
  common-frequency error or control variation.
- A separate non-learning bounded direct-action oracle must then show at least
  5% additional attainable improvement and nonconstant action targets on the
  same development scenarios.  This is the explicit anti-repeat gate for the
  earlier no-neural-residual failure.
- Failure of deterministic efficacy or oracle headroom stops this formulation.
  It does not authorize reward redesign, algorithm variants, or training.

### Ask Matt engineering handoff and TDD seams

- Route: current-context `/tdd`; no handoff, new task, or prototype.
- Pre-agreed public seams are one observation-adapter function, one immutable
  controller contract, one local-agent `act` seam, and one execution harness
  that accepts/returns a four-by-two action matrix.
- Red-green slices must prove the exact 50-to-60 conversion, rejection guards,
  per-agent locality, no global aggregation, sign symmetry, bounded action,
  slew, reset, nine-candidate identity, and zero-input behavior.
- Implementation success is engineering evidence only.  No test may claim
  plant efficacy, decoupling gain, learning headroom, or MARL value.

### Prospective comparison-identifiability decision

- **Decision**: `ALLOW` only for the next deterministic development gate under
  the frozen physical contract.  The full future direct-MARL comparison remains
  `BLOCK` until learner capacity/parameter sharing, optimizer/hyperparameters,
  interaction and tuning budgets, seeds/checkpoint selection, and the sealed
  evaluation bank/unit of analysis are frozen before training.  Inserting any
  old storage-power, common-scalar, edge-action, centralized observation,
  50-Hz objective, unmatched bound/timing, or unequal tuning arm is also
  `BLOCK`.
- **Identified estimand**: the bounded implementation effect of the selected
  deterministic controller and, later, the incremental effect of the one
  trained message-enabled direct-M/D implementation under this contract.
- **Stay-out claims**: controller-family superiority, MARL-class superiority,
  energy-feasible storage control, stability certificate, safety, topology
  generalization, EMT validity, and hardware readiness.

## Gate

`DESIGN-CONTRACT-PASS` requires all focused public-seam tests, compile, diff
check, round preflight, and independent static comparison audit to pass, with
no protected asset changed.  Otherwise return `STOP-UNIT-CONTRACT`,
`STOP-OBJECT-MATCH`, `STOP-IDENTIFIABILITY`, or `ENGINEERING-INCOMPLETE`.
PASS authorizes only the next separate deterministic efficacy and non-learning
headroom round.  It does not clear the still-blocked full learning-comparison
contract.  `training_authorized=false` in every branch.

## 资产保护契约

Protected `base_env.py`, `andes_vsg_env_v4.py`, `v4_config.py`, `train.py`,
`paper_grade_axes.py`, all old lines, old results, checkpoints, and claims stay
byte-unchanged.  Add only Q-0102/R366, one reusable new-line control module,
focused tests, this line's navigation correction, and the eventual R366
decision feed/claim/verdict.  R366 runs no ANDES process and writes no physical
trajectory.

## Cross-references

- CLM-0975 / R365: object, action mapping, information, differential-transient,
  and network-authority prerequisite PASS.
- `paper/paralleled_vsg_marl/ROUTE.md#phase-1--strong-deterministic-decoupling`.
- R365 audit findings D-001 and D-002.
