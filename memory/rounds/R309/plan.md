---
round: R309
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R309 plan — two-phase initialization/dynamic TDS canary

**Opened**: 2026-08-03
**Driver**: Q-0065; R308 met the sampled dynamic residual ceiling but failed
because its single strict tolerance was also consumed by TDS initialization.
**Parent**: CLM-0750 and the unchanged R308 two-trace contract.

## TL;DR

Test one explicit solver-phase transition: retain ANDES' default `1e-4`
tolerance through PFlow and 0.5-s TDS initialization, require valid
initialization, then switch exactly once to the already frozen `1e-10`
dynamic Newton tolerance before the first controlled step. Repeat only the
same OP1 zero and edge-2-negative traces. No sweep, full Stage 1, controller,
or training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0065 [opened R308] Can default-compatible TDS initialization acceptance be separated from strict post-initialization Newton convergence and pass the same two-trace canary without changing the plant, pulse, horizon, or residual gate?

## Recently Closed (last 3)

- Q-0064 closed-negative @ R308, by CLM-0750 — Does the R307 active-pulse algebraic-residual breach come from the TDS solve/readback contract, and can a prospective worst-case canary meet the unchanged 1e-8 gate without changing the plant or pulse?
- Q-0063 closed-negative @ R307, by CLM-0745 — Can the sealed model-first plant execute the frozen common and three-edge signed active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?
- Q-0062 closed-positive @ R306, by CLM-0740 — Can a separate physical-60-Hz model-first ANDES execution seam pass the frozen Stage-0 plant, coordinate, actuator, and telemetry invariants without changing legacy V4 semantics?

## Methodology

### Frozen two-phase solver contract

- Initialization phase: implicit trapezoid, `TDS.config.tol=1e-4`, derived
  `tol_zero=1e-10`, `TDS.test_ok is True`, scalar system exit code zero, and
  initialization endpoint `t=0.5 s`.
- Transition: after the initialization checks and before the first controlled
  step, switch exactly once to `TDS.config.tol=1e-10` and `tol_zero=1e-16`.
- Dynamic phase: preserve the R308 `max(abs(dae.g)) <= 1e-8` readback at every
  completed 0.2-s control-step boundary.
- Configuration must reject ambiguous simultaneous all-phase and post-init
  strict tolerances. Runtime records must expose both phases and switch count.

### Canary bank and TDD/EVAL

- OP1 only: device M/D 150/75, live system M/D 300/150, tie scale 1, SOC 0.30.
- One zero trace and one edge-2-negative trace. The `0.05` system-p.u. pulse,
  five active samples, twenty recovery samples, plant, graph, and all-zero M/D
  actions remain unchanged.
- TDD covers config phase semantics, fail-closed two-phase evaluation,
  create-only adapter behavior, and the stable `prepare/run/eval/analyse`
  surface. Existing EVAL-v2 tests remain mandatory regressions.
- The R309 `eval` command is execution-integrity-only and retains
  `EXTERNAL_AUTHORITY_REQUIRED`; it is not a paired efficacy comparison.

### Exact classification

- Any source/hash, trace identity/count, initialization phase, transition,
  time grid, finite telemetry, PFlow/TDS/exit, input, structural, M/D, or
  `max|g|` failure -> `INVALID-TWO-PHASE-TDS-CANARY`.
- Every guard true -> `TWO-PHASE-TDS-CANARY-PASS`; a separately sealed fresh
  full Stage 1 becomes eligible, but predictor/controller/training remain
  forbidden in R309.

## Gate

Both traces must pass the exact initialization and transition contract, contain
25 samples at 0.2-s increments, retain exit code zero and finite state, make no
M/D writes, read back dynamic tolerance `1e-10` and `tol_zero=1e-16`, and keep
every sampled `max(abs(dae.g)) <= 1e-8`. There is no alternate tolerance,
fallback, or outcome-selected rerun.

## 资产保护契约

- Immutable: R307/R308 seals and results, legacy V4/base environment, OP1,
  plant, pulse, time grid, horizon, readback point, and residual ceiling.
- Additive or bounded: one post-initialization solver field in the separate
  model-first config/env, one pure two-phase evaluator, focused tests, one R309
  adapter, and create-only R309 artifacts.
- Forbidden: tolerance or step sweep, threshold/plant/pulse repair, full Stage
  1, predictor/controller/optimization work, MARL, or neural training.

## Cross-references

- Q-0065; CLM-0750.
- `paper/decoupling_marl_model_first/working/model_contract.md` Stage-1
  execution-validity gate.
