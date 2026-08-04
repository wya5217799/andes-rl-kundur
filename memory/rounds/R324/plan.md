---
round: R324
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R324 plan - parameter provenance and open-loop time-step convergence

**Opened**: 2026-08-03
**Driver**: close Q-0079 before any actuator-constrained controller is formed.
**Parent**: CLM-0825; Q-0079; Q-0078.

## TL;DR

Bind every material parameter of the unchanged phasor-domain proxy and its
execution layer to a source, derivation, model default, or explicit modelling
assumption. Then execute one sealed OP0 edge-2-negative open-loop pulse at the
unchanged 0.2-s control period with 5, 10, and 20 TDS substeps. If both adjacent
refinements meet every frozen waveform, SOC, peak-timing, terminal-state, and
execution guard, return to Q-0078 on the unchanged plant. Otherwise stop
controller work and require plant/integration revalidation.

## Methodology

### Parameter-binding contract

The create-only seal must contain one row per material value with: identifier,
value, unit, base, represented object, source/locator, provenance class, and
calibration ceiling. Allowed provenance classes are `case-source`,
`literature-derived`, `official-model-default`, `derived`, and
`explicit-modelling-assumption`. An explicit assumption passes traceability but
must state that it is not a measured, manufacturer-identified, or calibrated
device value.

The inventory must cover, without omission:

- Kundur case identity, 100-MVA system base, 60-Hz nominal frequency, original
  G4 retained state, and disabled default line trip;
- four controlled proxy locations, device ratings, scheduled active power,
  inertia, damping, electrical parameters, radial-line values, added loads,
  and the separate low-inertia wind proxy;
- four storage locations, power and energy aggregation, current/power limits,
  active-current lag, SOC integrator, SOC bounds/initial value, efficiencies,
  active-power priority, reactive exclusion, and external ramp;
- 0.2-s control period, initialization horizon, TDS method and tolerances,
  substep refinement, pulse amplitude/sign/duration, and recovery duration.

No row may be labelled measured or manufacturer-derived without a direct
source. Correct unit conversion is not physical calibration.

### Frozen physical execution

- Plant: unchanged `AndesModelFirstEnv`, OP0, original Kundur G4 retained,
  default Toggler disabled, deterministic mode, zero communication failures,
  zero M/D writes, no load edit, initial SOC 0.50.
- Input: the existing Stage-1 `edge_2/negative` vector
  `[0, 0, -0.05, +0.05]` system p.u.; five active control samples followed by
  twenty zero-request recovery samples.
- Timing: control period 0.2 s. Use the existing `N_SUBSTEPS` precision seam at
  exactly 5, 10, and 20 substeps, corresponding to maximum segment lengths
  0.04, 0.02, and 0.01 s. Do not change the plant, pulse, controller period,
  operating point, integration method, or solver tolerances between runs.
- Solver: implicit trapezoid; initialization tolerance `1e-4` with tiny
  correction `1e-10`; post-initialization tolerance `1e-10` with tiny
  correction `1e-16`.
- Endpoints at every 0.2-s boundary: achieved four-device active power,
  physical frequency at the four controlled proxies, SOC, algebraic residual,
  solver/exit/finite guards, and saturation/limiter guards. Preserve terminal
  differential and algebraic state vectors for convergence comparison.
- EVAL: `NOT-APPLICABLE-OPEN-LOOP-CONVERGENCE`. There is no controller,
  performance comparison, reward, training, or efficacy estimand.

### Frozen convergence gates

Evaluate both adjacent pairs `(5,10)` and `(10,20)` without selecting a
preferred pair after outcome access. Every pair must satisfy:

- maximum achieved-power difference at control boundaries at most `5e-4`
  system p.u. (one percent of the frozen pulse amplitude);
- maximum physical-frequency difference at most `1e-3` Hz;
- maximum SOC difference at most `1e-6`;
- normalized terminal differential-state and algebraic-state L2 differences
  each at most `1e-4`, with denominator `max(1, ||fine||_2)`;
- absolute peak-time difference for achieved power and frequency deviation at
  most one 0.2-s control sample;
- identical 25-sample time grid, finite values, converged power flow and TDS,
  zero exit code, algebraic residual at most `1e-8`, exact requested/commanded
  pulse, unchanged M/D readback, no M/D write, Line 8 in service, and no
  external or internal power/current/recovery/SOC/energy guard failure.

## Gate

- `INVALID-MODEL-FIDELITY-CHECK`: seal/source/identity, parameter-inventory,
  execution, sidecar, replay, or no-controller/no-EVAL guard fails. No
  convergence metric is admissible.
- `PARAMETER-PROVENANCE-NO-GO`: execution is valid but at least one material
  value has no source, derivation, model default, or explicit-assumption
  binding. Stop Q-0078.
- `TIME-STEP-CONVERGENCE-NO-GO`: parameter binding and execution are valid but
  either adjacent refinement misses any frozen numeric gate. Version the
  integration contract and revalidate Stage 1 plus the reduced model before
  Q-0078.
- `MODEL-FIDELITY-GATE-PASS`: all parameter rows are honestly bound and both
  adjacent refinement pairs pass every gate. Close Q-0079 positive and make
  Q-0078 eligible on the unchanged plant.

No outcome authorizes a physical closed loop, controller efficacy claim,
distributed runtime, reward, agent, training, topology generalization, EMT or
hardware equivalence, or title-result claim.

## Engineering implementation and verification

- Put the formal classifier in `probes/r324_model_fidelity_validation.py`.
- Put the create-only seal/execute/analyse adapter in
  `scripts/run_r324_model_fidelity.py`; real ANDES execution is WSL-only through
  `scripts/andes_scratch.py`.
- Add focused unit and adapter tests before creating the seal. Run only those
  tests during implementation; run the full repository gates once at close.
- Seal all implementation and test hashes. Results are create-only JSON with
  SHA-256 sidecars and a manifest. Deterministic replay must reproduce the
  formal analysis byte-for-byte apart from the create timestamp.

## 资产保护契约

- Preserve R306--R323 plans, seals, results, feeds, claims, questions, and
  verdicts byte-for-byte. Preserve the conference title exactly.
- Do not modify the plant, protected V4/base environment, reduced-model bank,
  R321 examination, controller code, thresholds, or installed ANDES package.
- New durable assets are limited to the R324 plan, seal, execution adapter,
  validation probe, focused tests, result JSON/sidecars/manifest registration,
  one line-scoped feed, one claim, one verdict, Q-0079 disposition, and current
  line navigation/manifest refresh.
- Q-0078 implementation starts only in a separate prospective round after a
  valid `MODEL-FIDELITY-GATE-PASS`.

## Cross-references

- Platform and semantic audit: CLM-0825 and the R323 feed.
- Current fidelity blocker: Q-0079.
- Conditional actuator-constrained controller question: Q-0078.
- Existing signed pulse and execution seam: CLM-0770 and R312.
