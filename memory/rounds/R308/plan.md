---
round: R308
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R308 plan — prospective worst-case TDS convergence canary

**Opened**: 2026-08-03
**Driver**: Q-0064; R307 was invalid only because every nonzero trace crossed
the pre-registered algebraic-residual gate while the zero baselines passed.
**Parent**: CLM-0745 and the frozen R307 plant/pulse contract.

## TL;DR

Test one implementation-faithful solver configuration on the R307 zero
baseline and the observed worst case only. Keep the plant, pulse, time grid,
horizon, readback point, and `max|g| <= 1e-8` gate unchanged. Stop after the
two-trace canary; no parameter sweep, full Stage 1 rerun, controller, or
training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0064 [opened R307] Does the R307 active-pulse algebraic-residual breach come from the TDS solve/readback contract, and can a prospective worst-case canary meet the unchanged 1e-8 gate without changing the plant or pulse?

## Recently Closed (last 3)

- Q-0063 closed-negative @ R307, by CLM-0745 — Can the sealed model-first plant execute the frozen common and three-edge signed active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?
- Q-0062 closed-positive @ R306, by CLM-0740 — Can a separate physical-60-Hz model-first ANDES execution seam pass the frozen Stage-0 plant, coordinate, actuator, and telemetry invariants without changing legacy V4 semantics?
- Q-0061 closed-negative @ R305, by CLM-0735 — Do stable network configurations create locally observable topology-information value for genuine zero-sum VSG vector-inertia coordination?

## Methodology

### Source diagnosis and frozen repair

- ANDES 2.0.0 implicit trapezoid declares convergence when the largest Newton
  variable correction is at most `TDS.config.tol`; its default is `1e-4`.
- R307 read `dae.g` after every completed 0.2-s control step and observed a
  maximum `2.80045916331573e-6`, which is compatible with the default solver
  stopping while still failing the separately frozen paper gate.
- The only prospective repair is `tds_convergence_tolerance = 1e-10`, applied
  before PFlow/TDS execution together with ANDES' derived
  `TDS.tol_zero = tolerance / 1e6`. No alternative tolerance is run.

### Canary bank

- `OP1`: device M/D `150/75`, live system M/D `300/150`, tie scale `1`,
  initial SOC `0.30`.
- One zero-input trace and one `edge_2/negative` trace, the exact worst R307
  coordinate and sign.
- Pulse `-0.05 * B[:,2]` system p.u. for five 0.2-s samples, followed by
  twenty zero-request recovery samples. All M/D actions remain exactly zero.
- Public outputs must record configured tolerance, derived tiny-correction
  threshold, Newton/readback semantics, per-sample `max|g|`, and source hashes.
- TDD covers config validation/materialization, environment application and
  structural readback, fail-closed canary classification, create-only output,
  and the stable `prepare/run/eval/analyse` adapter surface.
- `eval` is a bounded execution-integrity evaluator for these two canary
  traces. It is not EVAL-v2's paired controller matrix and cannot support an
  efficacy claim. Existing EVAL-v2 tests remain mandatory regression checks.

### Exact classification

- Any source/hash, trace identity/count, time grid, finite telemetry,
  PFlow/TDS/exit, structural identity, M/D write/readback, solver-config
  readback, or `max|g|` failure -> `INVALID-TDS-CANARY`.
- Both traces valid and every sample has `max|g| <= 1e-8` ->
  `TDS-CANARY-PASS`; a fresh full Stage 1 may be proposed in a later round.
- The canary never authorizes predictor fitting, controller development, or
  training.

## Gate

Both traces must contain 25 samples at exact 0.2-s increments, retain the
R307 operating-point/action contract, complete PFlow/TDS with scalar exit code
zero and finite state, read back `TDS.config.tol == 1e-10` and
`TDS.tol_zero == 1e-16`, make no M/D writes, and satisfy
`max(abs(dae.g)) <= 1e-8` at every recorded control-step boundary. The zero
and pulse traces are equally load-bearing; there is no post-run fallback.

## 资产保护契约

- Immutable: all R307 seals/results/sources, legacy V4/base environment,
  model-first plant, OP1, pulse magnitude/sign/coordinate, time grid, horizon,
  readback point, and residual threshold.
- Additive or bounded: one optional strict-TDS field in the separate
  model-first config/env, focused host and WSL tests, one R308 adapter, and
  create-only R308 artifacts.
- Forbidden: tolerance or step-size sweep, plant/pulse/threshold repair,
  outcome-selected rerun, full Stage 1, predictor/controller work, training,
  or claim-bearing EVAL-v2 interpretation.

## Cross-references

- Q-0064; CLM-0745.
- `paper/decoupling_marl_model_first/working/model_contract.md` Stage-1
  execution-validity gate.
