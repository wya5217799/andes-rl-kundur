---
round: R272
state: completed
opened: '2026-07-26'
closed: '2026-07-26'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R272 plan — physically bounded classical active-power authority

**Status**: ACTIVE
**Opened**: 2026-07-26
**Driver**: Determine whether explicit, energy-feasible active-power actuation
creates a material common-frequency-restoration margin before any further
learned-control work.
**Parent**: CLM-0555, CLM-0560, CLM-0565
**Question**: Q-0034
**Reserved claim**: CLM-0570

## TL;DR

R270/R271 established that the current M/D-only proxy has useful transient
authority but no credible sustained power-balance state.  R272 adds a
separate, physically bounded `ESD1` active-power layer while preserving the
default V4 path and freezing all four VSGs at `M=200`, `D=100`.  A
prospectively fixed droop-plus-PI controller is compared once against a
matched zero-active-power-support system with identical ESD1 DAE structure on
a new 20-scenario no-anchor bank.  The original V4 system remains a secondary
structural contrast.  Both
full-horizon physical VSG-mean IAE and final-10-s common-frequency absolute
mean must improve by at least 2%, with paired uncertainty and all
failure/safety/action/energy guards passing.  No RL, GNN, topology claim,
unified GFM-BESS claim, or manuscript work is in scope.

## Snapshot at plan-time (oracle as of 2026-07-26)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0033 closed-positive @ R271, by CLM-0565 — Which implemented state determines terminal frequency after an M/D pulse ends?
- Q-0032 closed-negative @ R270, by CLM-0555 — Is there a nontrivial attainable-gain margin above droop in the current VSG actuation model?
- Q-0031 closed-negative @ R269, by CLM-0545 — Can an objective-aligned residual interface pass physical validity checks before retraining?

## Methodology

### Falsifiable objective

Under the frozen power, energy, SOC, headroom, ramp, lag, efficiency, and
converter-capability contract below, determine whether one independently
controlled classical active-power actuator improves both:

1. full-horizon physical VSG-mean IAE; and
2. final-window common-frequency absolute mean;

by at least 2% over a matched zero-active-power-support system with identical
storage DAE structure, without worsening completion, synchronization, peak,
RoCoF, action, or energy guards.

### Confirmed public seams for test-first work

The PI authorized the execution plan containing these seams before R272 was
reserved.  Tests will observe behavior only through:

1. `EnergyFeasibleBESSContract`: validates the physical specification and
   projects a requested system-base active-power vector into the common
   power/ramp/SOC/energy/capability contract.
2. `DroopPIActivePowerController`: `reset()` and `act()` expose deterministic
   classical control, anti-windup, and auditable requested power.
3. `AndesMultiVSGEnvV4Storage`: `reset()` and `step(...,
   bess_power_request_pu=...)` expose the independent ANDES storage channel
   without changing `AndesMultiVSGEnvV4`.
4. The R272 evaluator/runner: prepares immutable artifacts, resumes completed
   paired rows, and returns physical, terminal-window, action, energy,
   failure, tail, and paired-bootstrap evidence.

Each vertical slice follows red -> minimum green.  Tests use the real public
interface; ANDES itself is the only system boundary and is checked by WSL
smoke/integration tests rather than mocked.

### Frozen physical contract

The first-round model is explicitly a **hybrid authority proxy**: the existing
four `PV+GENCLS` VSGs remain the frequency-observation/fast-dynamics layer and
four independent grid-following `ESD1` devices provide active power at
Bus12/Bus16/Bus14/Bus15.  It is not a unified GFM-BESS and cannot support
inner-loop, fault-current, or EMT claims.

Capacity anchor:

- Gerini et al. experimentally report a `720 kVA / 560 kWh` BESS and
  round-trip efficiency at least `97%`:
  `https://doi.org/10.1016/j.epsr.2022.108567`.
- Each R272 equivalent aggregates exactly 50 such modules:
  `Sn = 36 MVA`, `En = 28 MWh`.
- Four equivalents therefore provide `144 MVA / 112 MWh` total.  The module
  count is an R272 feasibility-sizing assumption, not a claim about a real
  Kundur installation.  It was frozen before any new trajectory and gives
  total active-power authority close to, but below, the R268 development
  disturbance magnitude of `150 MW`.

Per-device frozen fields:

| Field | Frozen value | Source or derivation |
|---|---:|---|
| placement | Bus12, Bus16, Bus14, Bus15 | one independent ESD1 at each current VSG bus |
| `Sn` | 36 MVA | 50 x 720 kVA experimental modules |
| `En` | 28 MWh | 50 x 560 kWh experimental modules |
| `pmx` input | 1.0 device pu | converts to 0.36 pu on the 100 MVA system base |
| charge/discharge bound | symmetric +/-0.36 system pu | `ESD1.pmin=-pmx`; zero initial dispatch |
| `SOCinit` | 0.50 | midpoint of the WECC typical operating range |
| `SOCmin`, `SOCmax` | 0.20, 0.80 | conservative values inside WECC published typical ranges |
| initial energy headroom | 8.4 MWh each direction per device | `28 MWh x (0.50-0.20)` and symmetric charge side |
| `EtaC`, `EtaD` | sqrt(0.97) = 0.9848857802 | equal split of the reported minimum round-trip efficiency |
| active-current lag `tip` | 0.02 s | installed ANDES 2.0.0 `PVD1` default and implemented state |
| control update | 0.2 s | unchanged V4 control interval |
| external ramp | 0.36 system pu/s per device | conservative one-second zero-to-nameplate response |
| `pqflag` | 1, active-power priority | active-authority experiment |
| `qref`, `qmn`, `qmx` | 0 | reactive service excluded |
| `ialim` | 1.0 device pu | converter apparent-current/nameplate boundary |
| `Tf` | 1.0 | installed `ESD1` SOC-integrator scaling |
| static dispatch | 0 | symmetric positive and negative headroom |

The WECC energy-storage guideline is the source for the typical ranges
`SOCinit 20%-80%`, `SOCmin 10%-20%`, `SOCmax 75%-85%` and for blocking
charge/discharge at the corresponding limits:
`https://www.wecc.org/sites/default/files/documents/meeting/2024/ESD%20Modeling%20Guidelines%20-%20Final.pdf`.
NERC documents BESS active-power response on sub-cycle/cycle time scales and
the need to model headroom and duration; R272 deliberately applies the slower
one-second external ramp:
`https://www.nerc.com/globalassets/our-work/white-papers/fast-frequency-response-concepts-and-bps-reliability-needs.pdf`.

The installed ANDES 2.0.0 source is authoritative for implementation
semantics:

- `ESD1` integrates SOC with charge/discharge efficiency, limits at SOC
  bounds, and defines `pmin=-pmx`;
- `PVD1` supplies the 0.02-s active-current lag and current/capability limit;
- `DG.set_paux()` writes additive `Pext0` in system-base per unit.

Every source path, derivation, serialized contract byte string, and SHA-256
must be captured before the first new ANDES trajectory.  A unit, sign, or
conversion mismatch makes the round `INVALID`.

### Frozen plant and controller semantics

- Default `AndesMultiVSGEnvV4` remains byte-identical.
- All VSG M/D actions are zero in baseline and candidate:
  `M=[200,200,200,200]`, `D=[100,100,100,100]` throughout.
- Primary baseline and candidate both use the storage subclass, same ESD1
  devices, V4 config, disturbance, environment seed, timing, and zero M/D
  actions.  The baseline commands zero active power; the candidate uses PI.
- The original V4 system without ESD1 is a predeclared secondary structural
  contrast only and cannot determine the authority verdict.
- The primary controller is prospectively frozen as equal-sharing
  common-frequency droop plus PI:
  `Kp=2.0 system-pu/Hz/device`,
  `Ki=0.2 system-pu/(Hz s)/device`,
  nominal frequency from the real ANDES case, no deadband, conditional
  anti-windup, and the common physical VSG-frequency mean as input.
- `bess_p_f_droop` with the same `Kp=2.0` and `Ki=0` is a predeclared
  secondary mechanism comparison only.
- Constrained MPC is not implemented in R272.  Gate 1 asks whether a
  classical explicit-power channel has authority, and integral restoration
  supplies the most direct falsifier with substantially less design
  flexibility.  MPC remains dormant unless a later registered question is
  justified by this result.
- Development evidence may invalidate the contract or controller but cannot
  change gains, capacity, placement, threshold, horizon, or formal seed.

### Test-first and execution order

1. Contract schema and worked energy examples.
2. Power/ramp/SOC/capability projection and saturation reasons.
3. Droop and PI direction, reset, equal sharing, and anti-windup.
4. Storage environment zero-command/sign/unit/reset integration.
5. Evaluator terminal-window identity, failure retention, constraint checks,
   and paired statistics.
6. Existing V4 regression plus one real-ANDES 10-step storage smoke.
7. One full 300-step development trajectory per direction; only validity,
   not gain selection, is inspected.
8. Prepare and hash the new sealed bank and formal seal.
9. Run baseline/primary paired formal rows with `--resume`; run the droop-only
   secondary rows only after all primary rows exist.
10. Analyse once, issue a verdict/claim, close Q-0034, validate, and render.

### Scenario, time, and provenance contract

- Smoke/development cases come from the R268 envelope.  R272 uses one matched
  `PQ_0=-1.5` pair and one matched `PQ_0=+1.5` pair for controller validity
  only.  This four-trajectory budget was frozen after the first full trace
  established an approximately three-minute wall-clock cost and before any
  development performance endpoint was inspected.
- Formal bank: 20 new no-anchor scenarios generated by the existing
  `generate_test_scenarios(..., include_anchors=False)` with seed
  `2026072601`; bank path `memory/rounds/R272/scenario_bank.json`.
- The formal generator range remains its existing `[-3.0,+3.0]` pu on the
  100 MVA base with the existing 0.1-pu absolute floor.
- Environment seed: 42.
- Horizon: 300 steps = 60 s after disturbance, with the unchanged 0.2-s
  control interval.
- Final window: last 50 completed samples = 10 s.
- Paired bootstrap: 10,000 shared-index resamples, seed `2026072602`, 95%
  percentile interval.
- Controller order within each scenario alternates by scenario index to avoid
  a systematic execution-order confound.
- Failed or incomplete trajectories remain explicit rows and in every
  denominator.
- The bank, contract, plan, source files, environment config, controller
  config, and runner are hashed before the first formal trajectory.  Existing
  artifacts are reusable only when every expected hash and scenario/controller
  identifier matches.

### Frozen pre-formal artifacts

Generated after tests and development validity checks, before any formal
trajectory:

- actuator contract:
  `memory/rounds/R272/actuator_contract.json`
  SHA-256 `220559d9f6ae32fbce87c16552d75c7067481921072626ee8b627335a3e0ec4c`;
- 20-scenario no-anchor bank:
  `memory/rounds/R272/scenario_bank.json`
  SHA-256 `184d1233b0e75482b444e513857c3d28dc7d7af2f7fe9d0a59ba09da146901c7`;
- development validity:
  four of four 300-step trajectories completed without TDS failure or
  registered constraint violation; VSG M/D stayed exactly 200/100 and PI SOC
  remained within `[0.4853192692, 0.5112170186]`.

The seal-manifest hash is recorded in its immutable `.sha256` sidecar and the
formal runner command after the final source/plan hashing step; changing this
plan afterward would invalidate the seal.  Formal execution remains blocked
until that manifest exists and verifies.

### Test-first formal-seal correction

The first seal
`91b62bdcf527c33cf817a50f07e3282aad8944bc36292e1909fb5c8a05afe0b5`
was stopped after the first matched scenario produced two retained 6/300-step
TDS-failure rows.  The runner behaved correctly, but the sealed analyser still
required every row to complete and therefore could not honour the registered
failure-retention contract.  No completed formal performance endpoint was
opened or used for a design change.

R272 keeps the same bank, contract, capacity, controller gains, horizon,
thresholds, and environment seed.  Only failure-aware analysis is corrected:

- all 40 rows remain in completion/failure/constraint denominators;
- physical endpoints and paired bootstrap use the explicitly reported
  complete-pair subset only;
- any matched zero-support baseline failure classifies the formal contract as
  `INVALID`, rather than being silently dropped or interpreted as controller
  performance;
- the stopped seal, manifest, logs, and two failed trace files remain
  historical artifacts and are never overwritten;
- corrected formal output uses
  `results/r272_active_power_authority_v2` and a new immutable seal.

### Compute budget and stopping rule

- Unit/integration tests do not consume formal trajectory budget.
- Smoke: at most four 10-step real-ANDES trajectories.
- Development: exactly four full trajectories (two signed disturbances x
  baseline and primary); no gain or parameter sweep.
- Formal primary comparison: exactly 40 trajectories (20 paired scenarios x
  baseline/primary), unless a row fails, in which case the failed row still
  counts.
- Optional predeclared droop-only secondary: at most 20 additional formal
  trajectories and only after the primary set is complete.
- Optional original-V4 structural secondary: at most 20 trajectories and only
  after the primary set is complete.
- No second bank, capacity change, placement change, gain sweep, seed change,
  or horizon change after any formal outcome is visible.

## Gate

### Co-primary decision evidence

For `primary_minus_baseline`, compute the ratio-of-means percent change and
paired-bootstrap 95% interval for:

1. full-horizon physical VSG-mean IAE;
2. final-10-s common-frequency absolute mean.

Negative effects are improvements.

### AUTHORITY-POSITIVE

All conditions must pass:

- both co-primary mean effects are at most `-2%`;
- both paired-bootstrap interval upper bounds are below zero;
- candidate completion/TDS failure is no worse than baseline;
- normalized synchronization loss, worst-bus peak, and max sampled RoCoF are
  each no worse than `+5%`;
- active-power action L1 and total variation are each no worse than `+25%`
  for the frozen M/D layer (both primary arms use zero M/D action); BESS
  command variation is governed separately by the absolute power/ramp limits;
- zero SOC, energy, power, ramp, and converter-capability violations;
- all bank, contract, source, plan, environment, controller, runner, and trace
  hashes match.

Only this classification may open Gate 2.

### AUTHORITY-PARTIAL

The physical/provenance contract is valid, but exactly one co-primary passes
or a restoration gain is offset by a registered safety/action/energy guard.
Close Q-0034 without learning or topology work; any next question may diagnose
only the exact failed mechanism.

### NO-MATERIAL-AUTHORITY

The experiment is valid but the joint materiality/uncertainty gate is not
met.  Close this exact actuator/controller contract.  Do not rescue it with a
new capacity, gain, seed, bank, threshold, MPC, or learned controller.

### INVALID

Any initialization, interface, unit, sign, energy-accounting, numerical,
failure-retention, or provenance error blocks performance interpretation.
Repair correctness only under this active round.

## 资产保护契约

- Preserve every pre-R272 tracked and untracked user change.
- Do not edit the default behavior of V4, its existing config, checkpoints,
  R261-R271 artifacts, paper facts, or historical sealed banks.
- Add new storage/controller/evaluator code under new R272-specific public
  seams and new result namespaces only.
- Never overwrite a bank, trace, manifest, summary, or prior result.
- Run real ANDES only through `/home/wya/andes_venv/bin/python` in WSL, with
  at most three concurrent ANDES processes; R272 uses one.
- `geo` and `cum_rf` are diagnostics only.  Physical 60-Hz endpoints,
  failure, tail, action, and energy evidence carry the verdict.
- No staging, commit, push, PR, manuscript, or figure production is authorized.

## Cross-references

- Q-0034
- CLM-0555 — R270 fixed-library attainability result
- CLM-0560 — stop M/D-only learned-controller development
- CLM-0565 — explicit active-power/model correction required
- CLM-0570 — reserved R272 finding
- `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_landscape.md`
- `docs/research/2026-07-25_energy_feasible_multitimescale_vsg_execution_plan.md`
