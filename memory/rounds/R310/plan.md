---
round: R310
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R310 plan — fresh two-phase Stage-1 authority and coupling bank

**Opened**: 2026-08-03
**Driver**: Q-0066; R309 validated the two-phase solver seam, while R307's
full signed bank remains invalid and cannot be repaired or reused.
**Parent**: CLM-0755 and the frozen model-first Stage-1 contract.

## TL;DR

Execute a completely fresh 27-trace OP0--OP2 Stage-1 bank under the R309
two-phase TDS contract. Test signed common and three edge coordinates, physical
authority, SOC, zero-sum edge execution, observability, local linearity, and
measured retained cross-coupling. Run EVAL-v2 only after the complete fresh
18-edge-record matrix is sidecar-verified. Stop after classification; no
predictor, controller, optimization sweep, or training.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0066 [opened R309] Can a fresh two-phase-solver Stage-1 bank execute all signed common and edge active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?

## Recently Closed (last 3)

- Q-0065 closed-positive @ R309, by CLM-0755 — Can default-compatible TDS initialization acceptance be separated from strict post-initialization Newton convergence and pass the same two-trace canary without changing the plant, pulse, horizon, or residual gate?
- Q-0064 closed-negative @ R308, by CLM-0750 — Does the R307 active-pulse algebraic-residual breach come from the TDS solve/readback contract, and can a prospective worst-case canary meet the unchanged 1e-8 gate without changing the plant or pulse?
- Q-0063 closed-negative @ R307, by CLM-0745 — Can the sealed model-first plant execute the frozen common and three-edge signed active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?

## Methodology

### Fresh bank and unchanged physics

- OP0: device M/D 200/100, live system M/D 400/200, tie scale 1, SOC 0.50.
- OP1: device M/D 150/75, live system M/D 300/150, tie scale 1, SOC 0.30.
- OP2: device M/D 250/125, live system M/D 500/250, tie scale 2, SOC 0.70.
- Per point: one zero trace plus paired `+/-0.05` system-p.u. pulses for the
  common vector and source-positive edge columns `(0,1)`, `(1,2)`, `(2,3)`.
- Each pulse lasts five 0.2-s samples and is followed by twenty zero-request
  recovery samples. Every M/D action is exactly zero; no PQ edit occurs.
- Every trace initializes with TDS `tol=1e-4`, requires `test_ok=true`, exit
  code zero and endpoint 0.5 s, then switches exactly once to dynamic
  `tol=1e-10`, `tol_zero=1e-16` before the first controlled step.
- R307/R308 records and result hashes are forbidden inputs. All 27 records are
  newly executed from the R310 seal.

### Formal metrics and gates

- Reuse the R307 metric definitions and thresholds without outcome-dependent
  changes: request/command/internal matching `1e-12`, M/D readback `1e-10`,
  sampled `max(abs(g)) <= 1e-8`, final active-power tracking within 5%, edge
  command neutrality `1e-12`, achieved imbalance within 5% commanded L1, SOC
  in `[0.2,0.8]`, signal/drift at least 20, OP0 midpoint nonlinearity at most
  0.25, and all-point midpoint nonlinearity at most 0.50.
- Cross gains are measured and reported, never required to be small. This
  preserves the paper's decoupling claim as a measured-coupling problem rather
  than assuming exact modal separation.
- The action graph remains the three independent source-positive edge columns;
  no central scalar aggregation is introduced. Stage 1 establishes only the
  physical action premise for later distributed agents.

### EVAL trigger and optimization rules

1. Do not run EVAL before 27/27 source records and sidecars verify against the
   R310 run manifest and exactly 18 fresh edge records are present.
2. Prospectively derive an EVAL-only view: set scenario-level `sign=paired`,
   preserve polarity as `pulse_sign`, bind `source_record.path/sha256`, and
   deep-copy every other field. No trace rerun, threshold change, or authority
   change is allowed.
3. Run EVAL-v2 with `execution_profile=vector_power`, explicit active window
   1 s, 10,000 bootstrap resamples, and fixed seed 2026080310. It must report
   input integrity, execution contract, diagnostic pass, 18 records, and
   `EXTERNAL_AUTHORITY_REQUIRED`.
4. EVAL is an integrity gate, not an effect optimizer. Never tune pulse,
   plant, threshold, metadata, or controller from its scores in R310.
5. If `INVALID`, close R310 and allow only one new cause-specific small canary
   with unchanged scientific thresholds. If `STAGE1-AUTHORITY-NO-GO`, allow
   at most one registered single-factor non-learning diagnosis or stop the
   active-power path. If `STAGE1-PASS`, only predictor construction becomes
   eligible in a separate round; controller development and training remain
   forbidden.

### TDD seams

- Public fresh Stage-1 evaluator verifies R310 identity and the two-phase
  solver contract before delegating unchanged authority/coupling metrics.
- Public EVAL-view builder preserves source immutability and hash binding.
- Stable adapter exposes only `prepare`, `run`, `eval`, and `analyse`; every
  formal JSON is create-only with a SHA-256 sidecar.

## Gate

- Source/hash, freshness, trace matrix, solver-phase, PFlow/TDS/exit, time,
  finite-state, algebraic-residual, structural, sidecar, or EVAL integrity
  failure -> `INVALID-STAGE1-EXECUTION`.
- Valid execution but failed authority, M/D, achieved power, neutrality, SOC,
  limiter, signal/drift, or local-linearity guard ->
  `STAGE1-AUTHORITY-NO-GO`.
- All guards true -> `STAGE1-PASS`; predictor construction may be proposed in
  a later sealed round. Training is false in every branch.

## 资产保护契约

- Immutable: R306--R309 seals/results, legacy V4/base environment, frozen
  Stage-1 points/pulses/horizons/thresholds, action graph, title claim ceiling,
  and EVAL external-authority status.
- Additive or bounded: one fresh Stage-1 wrapper evaluator, one prospective
  EVAL-view seam, focused tests, one R310 adapter, and create-only R310 results.
- Forbidden: historical trace reuse, post-seal metadata/threshold repair,
  outcome-selected rerun, predictor fitting, controller implementation,
  optimizer sweep, MARL, or neural training.

## Cross-references

- Q-0066; CLM-0755.
- `paper/decoupling_marl_model_first/working/model_contract.md` sections
  `stage-0-and-stage-1-non-learning-probe-contract` and
  `training-and-eval-gates`.
