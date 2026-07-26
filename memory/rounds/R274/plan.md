---
round: R274
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R274 plan — prospectively screened active-power authority re-test

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Resolve the R272 INVALID result without post-hoc case deletion by
freezing a balanced nontrivial candidate bank, screening identical-DAE zero
support before any controller trace, and then reusing the exact R272
droop-plus-PI authority contract once.
**Parent**: CLM-0570, CLM-0575
**Question**: Q-0036
**Reserved claim**: CLM-0580

## TL;DR

R274 uses a three-stage state machine:

1. freeze a 24-case signed, four-location, three-severity candidate bank;
2. run zero-support completion screening only, retain every exclusion, and
   freeze the exact feasible subset plus nontriviality audit before any PI
   trace;
3. if and only if the screen passes, reuse the immutable screening traces as
   the formal baseline and run the frozen R272 droop+PI once on every included
   case.

No scenario is replaced, no gain/capacity/placement/model field changes, and
no candidate endpoint can influence the screen.  The R272 physical 60-Hz
co-primary endpoints, paired bootstrap, safety/action/energy guards, and
classification are reused.  No AI, GNN, topology, stability certificate,
cross-simulator, HIL, or manuscript work is in scope.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0036 [opened R273] Can active-power authority be tested validly on a prospectively completion-screened bank?

## Recently Closed (last 3)

- Q-0035 closed-positive @ R273, by CLM-0575 — Are R272's formal TDS failures caused by the disturbance envelope or by the added zero-support ESD1 DAE?
- Q-0034 closed-partial @ R272, by CLM-0570 — Does a physically bounded classical active-power actuator create material common-frequency-restoration authority?
- Q-0033 closed-positive @ R271, by CLM-0565 — Which implemented state determines terminal frequency after an M/D pulse ends?

## Methodology

### Falsifiable objective

Determine whether the exact R272 active-power controller has valid bank-level
common-frequency-restoration authority on a new prospectively feasible,
balanced and nontrivial disturbance set.  The comparison is valid only if:

- candidate generation is frozen before the first zero-support trajectory;
- zero-support screening is frozen before the first droop+PI trajectory;
- every included baseline completed 300/300 steps on the identical storage
  DAE;
- every excluded case remains in an immutable exclusion ledger;
- the included cases still satisfy the predeclared signed, location, severity,
  count, and mean-magnitude requirements.

### Confirmed public seams for test-first work

The user's standing request to continue Q-0036 authorizes tests at these
public seams:

1. `build_stratified_authority_candidates(...)` returns a deterministic,
   serializable candidate bank with explicit location/sign/severity metadata.
2. `assess_screened_authority_bank(...)` consumes only completion/provenance
   rows plus frozen strata and returns PASS/INVALID with the exact feasible
   subset and nontriviality checks.
3. `build_feasibility_screen_contract(...)` remains the public exclusion
   ledger and refuses to freeze after any controller trace exists.
4. The R274 runner exposes immutable `prepare-candidates`,
   `prepare-candidate-seal`, `screen`, `analyse-screen`,
   `prepare-formal-seal`, `evaluate`, and `analyse` stages.
5. Formal execution reuses the existing public
   `run_active_power_scenario(..., controller_name="droop_pi")`,
   `summarise_active_power_trace(...)`, paired bootstrap, and
   `classify_active_power_authority(...)` seams.  ANDES is the only system
   boundary and is never mocked.

Each slice follows red -> minimum green.  No private implementation or ANDES
internal call count is tested.

### Frozen physical and controller contract

R274 does not change the R272 actuator/controller implementation:

- physical contract:
  `memory/rounds/R272/actuator_contract.json`,
  SHA-256
  `220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c`;
- four independent 36 MVA / 28 MWh GFL ESD1 devices at
  Bus12/Bus16/Bus14/Bus15;
- SOC initial/min/max 0.50/0.20/0.80, symmetric 0.36-system-pu per-device
  power, one-second external ramp, active-priority capability projection,
  frozen efficiency and 0.02-s active-current lag;
- all four VSG normalized actions exactly zero, hence M/D exactly 200/100;
- primary controller exactly the R272 equal-sharing physical-60-Hz
  droop+PI: Kp=2.0 system-pu/Hz/device and
  Ki=0.2 system-pu/(Hz s)/device;
- matched baseline is the same storage DAE with zero requested active power;
- environment seed 42, 300 steps/60 seconds, unchanged 0.2-s control
  interval, final 50-step/10-s window;
- paired bootstrap 10,000 shared-index resamples, seed 2026072602;
- physical 60-Hz reporting remains separate from frozen V4 50-Hz control
  semantics.

The exact R272 runner/evaluator sources are hashed into both R274 seals.  Any
drift in contract, controller constants, environment, endpoints, runner, or
solver makes R274 INVALID.

### Candidate generation contract

The candidate generation seal is created before any new ANDES trajectory.

- candidate count: exactly 24;
- new RNG seed: 2026072603;
- locations: `PQ_0`, `PQ_1`, `PQ_Bus14`, `PQ_Bus15`;
- signs: positive and negative;
- severities:
  - `moderate`: absolute magnitude uniformly in `[0.65, 0.85]` pu;
  - `strong`: absolute magnitude uniformly in `[0.95, 1.15]` pu;
  - `edge`: absolute magnitude uniformly in `[1.35, 1.50]` pu;
- exactly one case for every location x sign x severity cell;
- magnitudes rounded to four decimals after sampling;
- stable names encode location, sign, and severity;
- candidate order is one deterministic RNG permutation, recorded in the bank;
- no paper anchor and no R272 formal case is copied.

The 1.50-pu ceiling is selected only from pre-controller completion evidence:
R272's signed PQ_0 development cases completed at +/-1.5 pu and R273 bounded
positive Bus14 completion at 1.530775 pu.  It is not inferred from droop+PI
performance and is not a universal feasibility assertion.

Candidate nontriviality is fixed before screening:

- all 8 location/sign strata have exactly 3 generated cases;
- all 3 severity tiers have exactly 8 generated cases;
- 8/24 generated cases are `edge`;
- generated mean absolute magnitude is at least 0.95 pu;
- generated maximum absolute magnitude is at least 1.35 pu.

Failure of candidate generation or its source/hash audit is INVALID before
ANDES.

### Completion-only zero-support screen

Screening runs the identical storage DAE with `zero_support` only.  Although
raw traces retain frequency samples for later paired analysis, the
screen/analyse-screen stages are forbidden to calculate, serialize, print, or
inspect controller-performance endpoints.  They may use only:

- setup/provenance validity;
- `completed`, `tds_failed`, `n_steps`, and requested steps;
- zero requested/commanded/actual BESS power;
- SOC exactly 0.5 for the zero-support arm;
- zero constraint violations;
- M/D exactly 200/100;
- location, sign, severity, trace hash, and solver termination evidence.

Every failed or invalid row is retained.  No redraw, replacement, magnitude
change, retry under a different seed, or discretionary down-selection is
allowed.

The screened formal subset is **all and only** candidate scenarios whose
single registered `storage_zero` row completed 300/300 with valid provenance
and zero physical-contract violation.

The screen passes only if all of the following prospectively fixed checks
hold:

- at least 20 of 24 candidates are included;
- excluded fraction is at most 4/24;
- each of the 8 location/sign strata retains at least 2 included cases;
- at least 6 included cases are from the `edge` tier;
- included mean absolute magnitude is at least 0.95 pu;
- included maximum absolute magnitude is at least 1.35 pu;
- every included baseline is complete and physically valid;
- no droop+PI trace exists at screen freeze.

If any check fails, R274 stops INVALID without running droop+PI.

### Two prospective seals

`candidate_seal.json` hashes the pre-result plan, candidate bank, R272
contract, generator, screen logic, R272 controller/evaluator, environments,
physical endpoints, runner, ANDES sources/config, package versions, and exact
execution contract before the first screen trajectory.

After all 24 screen traces exist, `analyse-screen` immutably writes:

- completion-only screen summary;
- feasibility-screen exclusion contract;
- all-and-only feasible formal bank;
- screen provenance with all 24 trace hashes.

`formal_seal.json` then verifies and hashes those artifacts, rehashes every
source/contract, proves `controller_trace_count_at_freeze=0`, and embeds the
immutable zero-support trace hashes as the formal baseline.  Only then may
droop+PI start.

The formal runner writes candidate traces to a separate namespace and never
rewrites a screen trace.  One missing or mismatched included baseline,
candidate, bank, screen, seal, or source hash is INVALID.

### Formal endpoint and failure evidence

The primary contrast is `droop_pi - zero_support`, using only scenarios where
both frozen baseline and candidate completed.  All included scenarios remain
in completion/failure denominators.

Continuous evidence reuses R272:

- full-horizon physical VSG-mean IAE;
- final-10-s common-frequency absolute mean;
- terminal common-frequency absolute error;
- normalized synchronization loss;
- worst-bus peak absolute frequency deviation;
- maximum sampled RoCoF;
- BESS command L1 and total variation;
- saturation fraction, min/max/terminal SOC;
- charge/discharge energy.

R274 additionally reports:

- paired completion table and exact failure counts;
- empirical upper-tail/CVaR evidence for both co-primary and safety endpoints;
- VSG normalized action L1/TV, which must remain exactly zero;
- maximum requested, projected-commanded, and actual BESS power;
- SOC, energy, ramp, and converter-capability violations/reasons;
- excluded fraction and included/excluded counts by location/sign/severity;
- every raw trace hash and measured simulator provenance.

No complete-pair endpoint can override an incomplete baseline/candidate or a
failed physical/provenance guard.

### Execution order and compute budget

1. Finish plan, red/green tests, Windows suite, WSL focused regression, Ruff,
   dual-metric lint, validation, and preflight.
2. Create/hash the 24-case candidate bank and candidate seal.
3. Run exactly 24 zero-support screen trajectories, one ANDES process, with
   resumable immutable rows.
4. Analyse screen once.  Stop INVALID if the screen gate fails.
5. If screen passes, create/hash the formal seal while proving zero existing
   droop+PI traces.
6. Run exactly one droop+PI trajectory per included scenario, one ANDES
   process, with resumable immutable rows.
7. Analyse once, audit hashes/physical contract independently, issue verdict
   and claim, update Q-0036, close R274, validate, render, and run the selector.

Screen trajectories are reused as the formal zero-support baseline, so no
baseline is rerun after the formal seal.  Maximum real-ANDES budget is 48
trajectories (24 screen + at most 24 candidate), all 300 steps unless a
retained TDS failure terminates early.  No development/gain-selection run,
secondary controller, second bank, or retry budget exists.

## Gate

The original R272 classifier and thresholds remain frozen.

### AUTHORITY-POSITIVE

All must pass:

- both co-primary ratio-of-means effects are at most -2%;
- both paired-bootstrap 95% interval upper bounds are below zero;
- droop+PI completion/failure is no worse than the feasible zero-support
  baseline;
- normalized synchronization loss, worst-bus peak and max sampled RoCoF are
  each no worse than +5%;
- VSG action L1 and TV remain exactly zero in both arms;
- zero SOC, energy, power, ramp, and converter-capability violations;
- candidate generation, screen, nontriviality, formal bank, two seals,
  source, contract, environment, solver, controller, endpoint, and every
  trace hash match.

Only AUTHORITY-POSITIVE may close Q-0036 positively and open Gate 2.

### AUTHORITY-PARTIAL

The full prospective experiment is valid, but exactly one co-primary passes
or a restoration gain is offset by a registered completion, safety, action,
or energy guard.  Gate 2 remains closed; no AI training starts.

### NO-MATERIAL-AUTHORITY

The experiment is valid but neither co-primary clears the frozen joint gate.
Close the exact R272 controller/actuator contract without gain/capacity/bank
rescue or learning.

### INVALID

Any candidate-generation, screen, nontriviality, initialization, interface,
unit, sign, energy-accounting, completion-retention, numerical, or provenance
error blocks performance interpretation.  Correctness may be repaired within
R274 only before candidate endpoints are opened.  After candidate evidence
exists, no bank/controller/threshold/source change is allowed.

## Outcomes

- **Joint material restoration**: both physical co-primary effects
  `<= -2%`, both paired 95% upper bounds `< 0%`, and every completion,
  safety, action, energy, screen and provenance guard passes
  -> `AUTHORITY-POSITIVE`.
- **One-sided/guard-limited restoration**: the prospective experiment is
  valid and at least one co-primary point improves, but exactly one endpoint
  or a registered completion/safety/action/energy guard prevents the joint
  gate -> `AUTHORITY-PARTIAL`.
- **No material restoration**: the prospective experiment is valid and
  neither physical co-primary improves under the frozen R272 classifier
  -> `NO-MATERIAL-AUTHORITY`.
- **Uninterpretable**: generated/included count below 20, excluded fraction
  above 4/24, fewer than 2 included cases in any location/sign stratum, fewer
  than 6 included edge cases, included mean magnitude below 0.95 pu, included
  maximum below 1.35 pu, any included zero-support failure/physical violation,
  or any source/artifact/trace mismatch -> `INVALID` before performance.
- R272's measured `r272_active_power_authority_v2` complete-pair effects
  (-58.10% IAE, -75.13% final-window error) are motivation only.  They are not
  an estimated R274 baseline, threshold, prior, or substitute for the new
  paired zero-support traces.

## 资产保护契约

- Preserve every pre-R274 tracked and untracked user change, including the
  teaching workspace.  Do not stage, commit, push, or open a PR.
- Never overwrite any R261-R273 plan, claim, question, seal, bank, trace,
  summary, provenance, checkpoint, result, or paper artifact.
- Do not alter default V4 behavior, V4Config, historical checkpoint semantics,
  the R272 physical contract, controller constants, storage placement, M/D,
  horizon, solver, endpoint definitions, or bootstrap rule.
- New code/artifacts use R274-specific modules, scripts, tests, namespaces,
  seals, and result directories only; shared R273 screen code may be extended
  only test-first before the candidate seal.
- Real ANDES runs only through
  `/home/wya/andes_venv/bin/python` in WSL, one process for R274.
- Physical 60-Hz endpoints carry the verdict; legacy 50-Hz, `geo`, and
  `cum_rf` cannot substitute for them.
- No AI/RL/GNN training, topology, certificate, cross-simulator, HIL,
  unified-GFM-BESS, EMT/fault-current, manuscript, or deployment claim.

## Cross-references

- Q-0036
- CLM-0570 — R272 active-power proxy implemented; original formal bank INVALID
- CLM-0575 — R273 shared envelope failure and conditional completion boundary
- CLM-0580 — reserved R274 finding
- `memory/rounds/R272/actuator_contract.json`
- `results/r273_storage_dae_feasibility/boundary_summary.json`
- `src/andes_rl_kundur/evaluation/feasibility_screen.py`
