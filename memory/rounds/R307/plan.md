---
round: R307
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R307 plan — Stage-1 signed power authority and coupling

**Opened**: 2026-08-03
**Driver**: Q-0063; R306 passed the implementation canary, but the conference
title still lacks signed edge-action authority and measured cross-coupling.
**Parent**: CLM-0740 and the frozen model-first Stage-1 contract.

## TL;DR

Seal and execute the smallest non-learning bank that tests one common and three
independent edge active-power coordinates at OP0--OP2. Use EVAL-v2 only as a
diagnostic cross-check. Stop after Stage-1 classification; no predictor,
controller, optimization sweep, or training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0063 [opened R307] Can the sealed model-first plant execute the frozen common and three-edge signed active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?
- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0062 closed-positive @ R306, by CLM-0740 — Can a separate physical-60-Hz model-first ANDES execution seam pass the frozen Stage-0 plant, coordinate, actuator, and telemetry invariants without changing legacy V4 semantics?
- Q-0061 closed-negative @ R305, by CLM-0735 — Do stable network configurations create locally observable topology-information value for genuine zero-sum VSG vector-inertia coordination?
- Q-0060 closed-positive @ R303, by CLM-0725 — Does heterogeneous BESS headroom make independent projection leak a zero-sum differential residual into the common-power coordinate?

## Methodology

### Frozen bank

- OP0 — device M/D 200/100, live system M/D 400/200, tie scale 1, SOC 0.50.
- OP1 — device M/D 150/75, live system M/D 300/150, tie scale 1, SOC 0.30.
- OP2 — device M/D 250/125, live system M/D 500/250, tie scale 2, SOC 0.70.
- Per point — one zero trace plus paired `+/-0.05` system-p.u. pulses for the
  common vector `[1,1,1,1]` and action-tree columns `(0,1)`, `(1,2)`, `(2,3)`.
- Pulse five 0.2-s samples; recovery twenty 0.2-s zero-request samples. Total
  27 traces, shared deterministic initialization and no PQ edit.

### TDD and EVAL seams

1. Public Stage-1 contract returns the exact operating bank and pulse vectors.
2. Public trace classifier consumes sealed records and returns guarded
   authority, sign, midpoint nonlinearity, signal/drift, and coupling metrics.
3. EVAL-v2 accepts an explicit active-window duration while retaining the
   historical 3-s default; the R307 edge-only signed matrix uses 1 s and the
   `vector_power` execution profile. Its status remains external-authority.
4. Stable adapter supports only `prepare`, `run`, `analyse`, and `eval`; all
   machine artifacts are create-only with SHA-256 sidecars.

### Exact metric definitions

- Frequency output is the inertia-weighted coordinate trace
  `xi = Q.T sqrt(M) (omega-1)` using each point's frozen live M.
- Paired signal is `0.5*(y_plus-y_minus)` after subtracting the matched baseline;
  numerical drift is the baseline deviation from its first sample. Required
  L2 signal/drift ratio is at least 20 for every coordinate pair.
- Midpoint nonlinearity is
  `||0.5*(y_plus+y_minus)-y_zero||_2 /
  max(0.5*(||y_plus-y_zero||_2+||y_minus-y_zero||_2),1e-15)`.
  OP0 maximum must be at most 0.25; all-point maximum at most 0.50.
- Finite-horizon cross gains divide the L2 norm of the opposite output
  coordinate by the L2 norm of the requested input. They are reported, never
  thresholded by smallness.

## Pre-registered classification

- Source/hash, trace-count, time-grid, PFlow/TDS/exit, finite telemetry,
  algebraic residual, Line_8/G4, structural identity, sidecar, or EVAL integrity
  failure -> `INVALID-STAGE1-EXECUTION`.
- Valid execution but failed request/command/internal authority, M/D readback,
  achieved-power sign/settling, edge neutrality, SOC direction/bounds, limiter,
  signal/drift, or nonlinearity gate -> `STAGE1-AUTHORITY-NO-GO`.
- All gates pass -> `STAGE1-PASS`; predictor construction becomes eligible in
  a later separately authorized round. Training remains false in every branch.

## Gate

Each trace must retain Stage-0 execution/timing/finite guards. Algebraic
residual must be at most `1e-8`; requests and external commands must match the
frozen pulse within `1e-12`; M/D readback tolerance is `1e-10`; no external or
internal limiter may activate. Final active achieved power must have the
requested sign and be within 5% of command. Edge request/command sums must be
within `1e-12`; final achieved imbalance must be at most 5% of commanded L1.
Positive achieved power decreases SOC and negative power increases SOC; all
SOC remains in `[0.2,0.8]`. EVAL-v2 must report diagnostic pass and
`EXTERNAL_AUTHORITY_REQUIRED`; formal authority remains this round's verdict.

## 资产保护契约

- Immutable: R306 seal/results/sources, legacy V4/base env, older rounds and
  manuscript lines, frozen thresholds, model-first working title.
- Additive or bounded: Stage-1 fields in the separate model-first config/env,
  one public Stage-1 evaluator, focused tests, one R307 adapter, R307
  create-only artifacts, and model-first line navigation after publication.
- Forbidden: post-seal threshold repair, outcome-selected points/amplitudes,
  predictor fitting, controller implementation, neural code, training, or
  claim-bearing EVAL interpretation.

## Cross-references

- Q-0063; CLM-0740.
- `paper/decoupling_marl_model_first/working/model_contract.md` sections
  `stage-0-and-stage-1-non-learning-probe-contract` and `training-and-eval-gates`.
