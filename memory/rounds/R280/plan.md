---
round: R280
state: completed
opened: '2026-07-27'
closed: '2026-07-27'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R280 plan — float32-aware correction of the R279 action audit

**Status**: ACTIVE
**Opened**: 2026-07-27
**Driver**: R279 completed all 192 formal trajectories but was classified
`INVALID` only because five projected float32 actions exceeded the nominal
slew threshold by less than one float32 ULP.
**Parent**: CLM-0605; Q-0041
**Reserved correction**: CLM-0610

## TL;DR

Without adding or rerunning any ANDES trajectory, determine whether R279's
`action_contract_all_rows=False` was a numerical-audit defect. Freeze a
representation-derived tolerance before corrected analysis, verify every
R279 seal and trace hash, and emit a separate correction summary that either
retains `INVALID` or reports the pre-registered efficacy branch.

## Snapshot at plan-time (oracle as of 2026-07-27)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?

## Recently Closed (last 3)

- Q-0041 closed-partial @ R279, by CLM-0605 — Do matched causal and centralized baselines explain the R278 shared-policy signal?
- Q-0038 closed-negative @ R278, by CLM-0600 — Does one learned zero-sum inertia allocator outperform the frozen reference on unseen disturbances?
- Q-0040 closed-positive @ R277, by CLM-0595 — Is there an attainable disturbance-adaptive differential-inertia margin above the sealed classical reference?

## Methodology

### Tight feedback loop

Add a regression test at the real `audit_icems_policy_action()` seam:

- a recorded R279-style slew of `0.2500000074505806` must be accepted because
  it lies within one float32 ULP of the frozen `0.25` limit;
- a value more than one float32 ULP above the limit must still fail.

The red/green command is:

`python -m pytest tests/test_icems_residual_evaluation.py -q`

### Ranked hypotheses

1. Float32 projection plus a fixed `1e-9` audit tolerance caused false
   failures. Prediction: one float32 ULP accepts exactly the five observed
   slew rows and changes no other guard.
2. Recorded `q` is not the executed projected value. Prediction: observed
   excesses exceed the representation bound or disagree with action telemetry.
3. Eight-worker execution corrupted traces. Prediction: trace hashes,
   completion, or unrelated guards fail.
4. Active-window reset creates a real slew discontinuity. Prediction:
   failures concentrate at the 3-s boundary and exceed the representation
   bound.

### Frozen numerical rule

For float32-projected scalar magnitude and slew limits, allow exactly one
representable float32 spacing at the positive contract bound:

`tol(limit) = spacing(float32(abs(limit)))`.

This rule is derived from the execution dtype and limit, not chosen from the
R279 efficacy outcome. The existing physical-zero-sum representation tolerance
is unchanged.

### Corrected analysis

Create a new R280 analysis entry point and output directory. It must:

1. verify the R279 formal seal, summary, provenance, and all 192 trace hashes;
2. recompute all action audits from the immutable traces;
3. confirm the only old failures were the five sub-ULP slew rows;
4. retain all R279 efficacy estimates and apply the already registered R279
   decision tree with corrected validity;
5. write new, no-overwrite correction summary/provenance artifacts;
6. never modify R279 seals, summaries, traces, checkpoints, or verdict.

## Gate

- **AUDIT-CORRECTION-VALID**: every upstream hash verifies; exactly the five
  registered sub-ULP slew rows change false-to-true; no other audit changes;
  all 192 rows pass; the corrected classification follows the unchanged R279
  decision tree.
- **R279-INVALID-CONFIRMED**: any slew excess is above one float32 ULP, any
  other guard failure remains, or corrected validity is false.
- **CORRECTION-INVALID**: any upstream hash/source/trace mismatch, output
  overwrite, or decision-rule drift is detected.

## 资产保护契约

- No ANDES simulation, training, new seed, new bank, or controller execution.
- Do not edit `paper/icems2026/**` or its PDF in R280.
- Do not overwrite or relabel any R279 artifact; CLM-0610 may supersede
  CLM-0605 only through a separately hashed correction result.
- Preserve all unrelated user changes in the dirty worktree.

## Cross-references

- CLM-0605: immutable R279 `INVALID` finding being audited.
- Q-0041: reopened only to resolve the identified numerical validity defect.
- `memory/rounds/R279/formal_seal.json`
- `results/r279_formal_evaluation/formal_summary.json`
- `results/r279_formal_evaluation/provenance.json`
