---
round: R367
state: aborted
manuscript_line: paralleled-vsg-marl
opened: '2026-08-12'
closed: '2026-08-12'
supersedes_rounds: []
superseded_by_round: null
abort_reason: Formal attempt failed before analysis with BrokenPipeError after the
  external command output pipe closed; immutable failure retained and no retry attempted.
superseded_note: null
---
# R367 plan — deterministic efficacy and conditional-headroom gate

**Opened**: 2026-08-12
**Driver**: Test whether the R366 object-matched deterministic family both
works on the four-VSG plant and leaves a non-learning, time-varying target
worth learning before any neural training.
**Parent**: Q-0103; CLM-0980; R366

## TL;DR

Workload: `evidence`.  Execute zero action and the nine frozen local-neighbour
M/D candidates on eight balanced development scenarios.  Select one global
candidate, then derive a non-deployable per-scenario best-of-nine oracle only
from fully executed trajectories.  Training stays forbidden.  Failure of
either the deterministic efficacy gate or the oracle-headroom gate stops this
formulation.

## Snapshot at plan-time (oracle as of 2026-08-12)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0102 closed-positive @ R366, by CLM-0980 — Can the fixed-title line freeze a 60-Hz, permission-matched per-VSG inertia/damping comparison contract and a deterministic baseline family that leaves a falsifiable learning gate without importing the old action-object mismatch or claiming storage feasibility?
- Q-0101 closed-positive @ R365, by CLM-0975 — Does the existing ANDES V4 candidate provide four separately addressable VSG agents with independent bounded inertia and damping actions, causal local-neighbour observations, measurable differential dynamics, and nonzero network-transmitted action authority?
- Q-0100 closed-positive @ R363, by CLM-0965 — On the exposed development bank, does adding a common residual-power channel to the three-edge zero-common action basis enlarge the per-case physical action-space headroom, showing that the zero-common residual contract itself (rather than information) limits the R358 feasibility?

## Methodology

### Research Supervisor result gate

- **Question**: on the verified four-VSG M/D object, does one fixed member of
  the R366 deterministic family materially reduce differential-frequency
  energy without common-frequency or actuator-stress harm, and does
  scenario-conditional selection within the same bounded family leave at
  least five percent additional headroom with genuinely time-varying actions?
- **Scientific object**: four VSG parameter objects at buses `(12,16,14,15)`,
  each with one causal seven-field local/neighbour observation and its own
  bounded two-coordinate M/D action.
- **Unit of analysis**: one deterministic disturbance scenario.  This is a
  complete finite development bank, not a population sample; report all eight
  paired scenarios and aggregate ratios, with no inferential population claim.
- **Inference ceiling**: development-only evidence about this finite
  implementation on one modified-Kundur plant.  The oracle is an unattainable
  outcome selector, not a deployable controller, MARL result, stability
  certificate, safety result, topology result, or hardware result.

### Frozen development bank and plant

- Reuse only scenario definitions from the older screened bank, never its
  trajectories or results.  Select all and only `severity=strong` cases: four
  load locations crossed with positive and negative signs, for eight scenarios.
- Every arm uses seed `42`, 30 decisions, 0.2 s per decision, zero delay, zero
  dropout, physical 60-Hz reporting, and the same heterogeneous baseline
  damping vector `(70,90,130,150)` with M baseline 200.
- Arms are `zero` plus the exact nine R366 gain pairs.  Every scenario-arm pair
  gets a fresh environment and controller reset.  The reward is neither read
  nor used for selection.

### Endpoints and selection

- Primary: time integral of mean squared per-VSG frequency deviation from the
  instantaneous four-VSG mean, in Hz squared seconds.
- Secondary: analogous differential active-power energy, in per-unit squared
  seconds.
- Common-mode guard: time integral of absolute instantaneous mean frequency
  error from 60 Hz.  The selected controller's aggregate value may not exceed
  105% of zero action.
- Actuator guards: no bound or slew violation, no additional failed scenario,
  and at most 5% of coordinate-time samples at the normalized action bounds.
  Boundary-aware total variation is reported but is not divided by the zero
  arm's identically zero variation.
- Select among guard-passing candidates by minimum aggregate primary, then
  aggregate secondary, then frozen candidate name.  Deterministic PASS requires
  at least 10% aggregate primary improvement over zero.

### Prospective correction of the R366 control-variation wording

R366 stated a five-percent relative no-harm limit for control variation versus
zero action.  That denominator is identically zero, so the test is undefined
and would reject every nonconstant controller.  Before any R367 outcome is
visible, replace only that malformed comparison by the explicit actuator
guards above: zero bound/slew violations and at most 5% bound-contact samples.
Keep total variation as a reported endpoint.  The deterministic 10%, oracle
5%, common-frequency 5%, failure, and nonconstant-action thresholds are
unchanged.

### Non-learning headroom oracle

- For each scenario, select after execution the valid candidate with minimum
  primary, then secondary, then frozen name.  This best-of-nine outcome
  selector has access to completed outcomes and is therefore explicitly
  non-deployable and excluded from later comparator claims.
- Compare the sum of its eight selected primary values with the sum from the
  one globally selected deterministic candidate.  Oracle PASS requires at
  least 5% additional improvement.
- Every oracle-selected executed trace must have boundary-aware total variation
  greater than `1e-6`, and the bank must select at least two distinct candidate
  names.  These guards reject a static or single-controller relabelling.

### Design red-team and comparison-identifiability return

- Outcome leakage is allowed only inside the explicitly non-deployable oracle;
  it cannot become a policy, comparator, checkpoint selector, or test input.
- The global candidate and oracle share plant, disturbances, observations,
  action coordinates, bounds, slew, update rate, family, and execution count.
  The oracle differs only by privileged outcome-dependent per-scenario
  selection, so its only identified role is an upper bound on conditional
  selection value.
- Strongest alternative explanation: gains merely change common damping rather
  than differential coordination.  The primary differential endpoint plus the
  common-mode no-harm guard distinguishes the registered gate, while action-row
  dispersion is retained as descriptive telemetry.
- Result decision is `ALLOW` only for the bounded development conclusions.
  Full MARL comparison stays `BLOCK` regardless of result until the six R366
  learning/tuning/selection/evaluation budgets are prospectively frozen.

### Ask Matt engineering handoff and TDD seams

- Route: current-context `/tdd`; no new task, prototype, or handoff.
- Pre-agreed public seams are a pure JSON-serializable experiment contract, a
  pure trace summarizer, and a pure complete-bank classifier.  The formal WSL
  runner is tested through its command and create-only artifact boundary.
- Red-green slices must prove balanced bank identity, deterministic global
  selection, common/action guard rejection, per-scenario oracle selection,
  the 10%/5% thresholds, nonconstant/distinct selection guards, invalid record
  handling, and training prohibition.

## Gate

- `DETERMINISTIC-AND-HEADROOM-PASS`: deterministic and oracle gates both pass.
  This closes the pretraining mechanism question but does not authorize
  training.
- `STOP-DETERMINISTIC-NO-EFFICACY`: no globally fixed candidate clears the
  deterministic threshold and all guards.
- `STOP-NO-CONDITIONAL-HEADROOM`: deterministic gate passes but the oracle does
  not clear both the incremental and nonconstant/distinct-target guards.
- `ANALYSIS-INVALID`: missing scenario-arm pair, failed provenance, malformed
  trace, incomplete execution, or actuator mapping violation.  No retry after
  seal is authorized; repair requires a successor round.

## Formal launch contract

- formal_entry: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r367_deterministic_headroom.py execute --expected-seal-sha256 <sha256>`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r367_deterministic_headroom.py rehearse`
- rehearsal_scope: `same-pre-attempt-path`; verify the same plan/question,
  source, installed ANDES/case, contract, process, and output-absence guards
  used by formal execution without creating a physical trajectory.
- rehearsal_checks: source_hash, parent_hash, installed_package, installed_case, output_absence
- wsl_python_processes: 1
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R367/capacity_evidence.json`
- host_process_budget: 1
- other_reserved_processes: 0
- Capacity method: one
  representative five-step zero-action scenario after rehearsal; record wall
  time, peak resident memory, free disk, host/WSL memory, installed runtime,
  and other research processes.  It is capacity evidence only for the frozen
  serial budget.
- The serial budget is derived prospectively from the representative
  measurement and the absence of a need to engineer parallel workers for an
  expected short finite bank.  Measure other processes immediately before
  capacity and formal launch, otherwise HOLD.
- Formal completion requires all 80 scenario-arm traces plus analysis and
  manifest sidecars.  Engineering failure, hash drift, resource collision,
  or incomplete bank makes the attempt invalid.  Scientific early stop is not
  used.  Retry and training are both unauthorized.
- Monitor only process liveness, completed arm count, terminal artifacts, and
  resource failures; do not inspect scientific endpoints until all arms finish.

## 资产保护契约

Protected environment/config/training files, all old lines, old trajectories,
checkpoints, claims, and results stay byte-unchanged.  Add only Q-0103/R367,
one pure evaluation module, one formal runner, focused tests, fresh R367
results, and this line's feed/claim/verdict/navigation pointers.  Old scenario
definitions are read-only design inputs; old measurements never enter R367.

## Cross-references

- CLM-0980 / R366: unit-valid observation, per-VSG M/D action, deterministic
  family, and pretraining thresholds.
- CLM-0975 / R365: physical object, mapping, information, differential dynamics,
  and network-transmitted action authority.
- `paper/paralleled_vsg_marl/ROUTE.md#phase-1--strong-deterministic-decoupling`.
