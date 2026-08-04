---
round: R311
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R311 plan — source-bound Stage-1/EVAL record-guard canary

**Opened**: 2026-08-03
**Driver**: Isolate the single R310 adapter-contract failure before any new physical bank or learning work.
**Parent**: CLM-0760; Q-0067

## TL;DR

Add one pure, fail-closed Stage-1-to-EVAL record-guard synthesizer and test it
on one immutable R310 positive/negative edge pair. Run EVAL-v2 only as a
non-claim-bearing integration canary. Do not rerun physics or amend R310.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0067 [opened R310] Can one explicit Stage-1-to-EVAL record-guard synthesis pass a small source-bound adapter canary without changing source records, scientific thresholds, or the R310 verdict?

## Recently Closed (last 3)

- Q-0066 closed-negative @ R310, by CLM-0760 — Can a fresh two-phase-solver Stage-1 bank execute all signed common and edge active-power probes across OP0--OP2 with valid authority, local linearity, and measured common-differential coupling?
- Q-0065 closed-positive @ R309, by CLM-0755 — Can default-compatible TDS initialization acceptance be separated from strict post-initialization Newton convergence and pass the same two-trace canary without changing the plant, pulse, horizon, or residual gate?
- Q-0064 closed-negative @ R308, by CLM-0750 — Does the R307 active-pulse algebraic-residual breach come from the TDS solve/readback contract, and can a prospective worst-case canary meet the unchanged 1e-8 gate without changing the plant or pulse?

## Methodology

### Frozen source pair

- Positive: `results/r310_model_first_stage1/records/edge_source/op0_edge_0__positive.json`, SHA-256 `db59415d00238cbd58339c52671e67a8926d517ca0a464a89f49fdffb3bba17d`.
- Negative: `results/r310_model_first_stage1/records/edge_source/op0_edge_0__negative.json`, SHA-256 `eae0611606d0bc543c7d038f0a91d589f9d0822cf119e1d2be4d42f3a061c7a1`.
- The corresponding sidecars must verify before view construction. The files
  are immutable fixtures, not repaired scientific evidence.

### TDD contract

1. RED: a public synthesizer is absent; tests require the exact EVAL-v2
   mapping `completed=true`, `tds_test_ok=true`, `system_exit_code=0`, and
   `finite_telemetry=true` from authoritative Stage-1 source fields.
2. GREEN: implement one pure function that deep-copies nothing and rejects
   missing, false, nonzero, incomplete, non-finite, or inconsistent source
   state. It must not trust a pre-existing source `guards` object.
3. REFACTOR: a guarded-view builder composes the frozen R310 paired-metadata
   view with the synthesized mapping and source path/hash without mutating the
   source record.
4. Adapter commands are `prepare`, `run`, and `analyse`; all formal artifacts
   are create-only with SHA-256 sidecars.

### EVAL trigger

- Run only after the seal, both source JSON sidecars, source identities, and
  source hashes verify.
- Use `vector_power`, baseline `positive`, required active window 1.0 s,
  1000 bootstrap resamples, and seed 2026080311.
- The canary requires one complete paired scenario and retains
  `EXTERNAL_AUTHORITY_REQUIRED`. No endpoint or family-effect value may be
  interpreted.

## Gate

- `EVAL-GUARD-ADAPTER-CANARY-PASS` only if the two source bindings remain
  exact, EVAL input integrity passes, EVAL execution contract passes with zero
  violations, diagnostic_pass is true, and external authority remains
  required.
- Otherwise `INVALID-EVAL-GUARD-ADAPTER-CANARY`; stop and preserve the failure.
- A PASS authorizes only a separately sealed fresh Stage-1 design review. It
  does not repair R310 or authorize predictor, controller, distributed-agent,
  MARL, optimization, or training work.

### Outcomes

- All registered integrity and execution checks true with zero violations:
  `EVAL-GUARD-ADAPTER-CANARY-PASS`; close only the adapter-contract question.
- Any missing/mismatched source binding, false integrity check, execution
  violation, false diagnostic pass, or authority-status drift:
  `INVALID-EVAL-GUARD-ADAPTER-CANARY`; preserve artifacts and stop.
- No numerical endpoint magnitude, bootstrap result, controller-family effect,
  or physical pair metric changes either classification.

## 资产保护契约

- Unchanged: every R310 source/result/view/scorecard/analysis/provenance byte,
  plant, pulse, operating points, scientific thresholds, classification, and
  claim ceiling.
- Added: one pure guard-synthesis module, unit tests, one R311 adapter, seal,
  two derived guarded views, diagnostic scorecard, analysis, and provenance.
- No ANDES execution and no physical trace generation occur in R311.

## Cross-references

- Parent failure: CLM-0760.
- Question: Q-0067.
- Non-claim-bearing diagnostic authority: EVAL-v2 with
  `EXTERNAL_AUTHORITY_REQUIRED`.
