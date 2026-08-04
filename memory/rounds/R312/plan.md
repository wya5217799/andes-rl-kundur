---
round: R312
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R312 plan — fresh Stage-1 bank with sealed EVAL guard synthesis

**Opened**: 2026-08-03
**Driver**: Obtain the first valid end-to-end signed authority and coupling bank without reusing invalid R310 outcomes.
**Parent**: CLM-0755; CLM-0760; CLM-0765; Q-0068

## TL;DR

Execute a new 27-trace OP0--OP2 Stage-1 bank under the R309 two-phase solver
and the R311 fail-closed EVAL record-guard seam. Preserve every R310 physical
threshold but reuse none of its records, views, scorecards, metrics, or
analysis. Stop before predictor, controller, optimization, or training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0068 [opened R311] Can a separately sealed fresh 27-trace Stage-1 bank using the R309 two-phase solver and R311 record-guard seam pass the full authority, linearity, coupling, and EVAL integrity contract?

## Recently Closed (last 3)

- Q-0067 closed-positive @ R311, by CLM-0765 — Can one explicit Stage-1-to-EVAL record-guard synthesis pass a small source-bound adapter canary without changing source records, scientific thresholds, or the R310 verdict?
- Q-0066 closed-negative @ R310, by CLM-0760 — Can a fresh two-phase-solver Stage-1 bank execute all signed common and edge active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?
- Q-0065 closed-positive @ R309, by CLM-0755 — Can default-compatible TDS initialization acceptance be separated from strict post-initialization Newton convergence and pass the same two-trace canary without changing the plant, pulse, horizon, or residual gate?

## Methodology

### Frozen physical bank

- OP0: VSG M/D device values 200/100, tie scale 1, initial SOC 0.5.
- OP1: VSG M/D device values 150/75, tie scale 1, initial SOC 0.3.
- OP2: VSG M/D device values 250/125, tie scale 2, initial SOC 0.7.
- Per point: zero plus positive/negative common and edge-0/1/2 probes, for
  exactly 27 fresh traces. Positive coordinates and signs are those in the
  sealed model-first contract.
- Pulse: 0.05 system p.u.; five 0.2-s active samples followed by twenty 0.2-s
  recovery samples. GENCLS M/D actions remain zero.
- Solver: initialize through 0.5 s with ANDES defaults `tol=1e-4` and
  `tol_zero=1e-10`, then switch exactly once before control to dynamic
  `tol=1e-10` and `tol_zero=1e-16`.

### Frozen scientific guards

- Exact 27-record R312/Q-0068 identity and seal; no R307, R308, or R310 source
  artifact enters the bank.
- PFlow/TDS success, exit zero, finite physical 60-Hz telemetry, two-phase
  solver readback, unchanged physical topology, live M/D readback, and
  `max(abs(dae.g)) <= 1e-8` on every post-control sample.
- Requested, commanded, external-readback, internal-reference, and achieved
  active-power authority; edge zero-sum neutrality; SOC direction/bounds; no
  limiter or saturation; observable response; paired local linearity.
- Signal-to-baseline-drift ratio at least 20; OP0 midpoint nonlinearity at
  most 0.25; all-point midpoint nonlinearity at most 0.50. Common-to-
  differential and differential-to-common gains are measured, not assumed
  zero.

### EVAL trigger and rules

1. Do not run EVAL before all 27 source records and sidecars verify against
   the R312 manifest and exactly 18 fresh edge records are present.
2. Build source-hash-bound paired views with the R311 fail-closed guard
   synthesis. No source mutation or physical rerun is allowed.
3. Use EVAL-v2 `vector_power`, baseline `positive`, 1-s active window, 10000
   bootstrap resamples, and seed 2026080312; authority remains
   `EXTERNAL_AUTHORITY_REQUIRED`.
4. EVAL is an execution-integrity gate, not an effect optimizer. No in-round
   pulse, plant, threshold, metadata, predictor, controller, or training tune
   is allowed after outcomes.
5. INVALID permits only a new cause-specific canary. AUTHORITY-NO-GO permits
   one registered single-factor nonlearning diagnosis or stop. PASS permits
   predictor construction only in a separate round.

### TDD and adapter

- Generalize the paired-view identity seam prospectively while preserving the
  R310 default behavior; tests must cover both identities and reject drift.
- The R312 adapter exposes only `prepare`, `run`, `eval`, and `analyse` and
  writes create-only JSON plus SHA-256 sidecars.

## Gate

- `INVALID-STAGE1-EXECUTION` if any source, solver, physical, structural, or
  EVAL integrity guard fails. Do not interpret pair metrics.
- `STAGE1-AUTHORITY-NO-GO` only when execution is valid but signed authority,
  observability, SOC, neutrality, limiter, or registered local-linearity gates
  fail.
- `STAGE1-PASS` only when every registered guard passes; this authorizes only
  separate predictor construction, not controller development or training.

### Outcomes

- All guards true: `STAGE1-PASS`; register bounded signed-authority and
  measured-coupling evidence for the tested modified Kundur plant.
- Valid execution but one or more scientific authority guards false:
  `STAGE1-AUTHORITY-NO-GO`; preserve results and follow the frozen diagnosis
  rule.
- Any execution or EVAL-integrity guard false: `INVALID-STAGE1-EXECUTION`;
  preserve results and allow only a cause-specific canary.
- No pair-metric magnitude changes the registered decision tree after results.

## 资产保护契约

- Unchanged: plant, topology, operating points, pulse, horizon, R309 solver
  phases, all R310 scientific thresholds, classification, and no-training
  ceiling.
- Added: R312 identity support, guarded-view tests, one R312 adapter, seal,
  fresh physical records, guarded views, EVAL scorecard, analysis, and
  provenance.
- Forbidden: R310 record/view/scorecard/metric reuse or amendment, outcome-
  selected rerun, predictor fitting, controller implementation, MARL, or
  neural training.

## Cross-references

- Solver precondition: CLM-0755.
- Invalid end-to-end predecessor: CLM-0760.
- Guard-seam canary: CLM-0765.
- Question: Q-0068.
