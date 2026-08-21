# R387 evidence and power-system domain audit

## Coverage and authority

- Scope: `paper/converter_vsg_pq_decoupling/reports/R387.md`, `CLM-1080`,
  `paper/converter_vsg_pq_decoupling/working/R387_diagnosis.md`, the R387
  plan/seal/verdict, and the four
  create-only result JSON files.
- Evidence precedence: formal seal and immutable result/sidecar artifacts;
  final formal classifier; round plan and repository validity rules; strict
  diagnosis; claim/feed wording. The diagnosis and this audit cannot revise a
  formal artifact.
- Deterministic inventory: one feed scanned; 57 evidence-sensitive lines, one
  claim ID, and two round IDs. The inventory resolves CLM-1080 and identifies
  R387 as invalid, consistent with the feed's exclusion language.
- Presentation, venue, citation, novelty, and manuscript cross-section checks
  are not applicable to this pre-draft invalidity feed.

## Claim-evidence audit

| ID | Location and atomic claim | Type/scope | Canonical source and locator | Verification | Status | Safe wording |
|---|---|---|---|---|---|---|
| E-001 | Feed Identity/Conclusions: R387 is analysis-invalid | validity | `formal_analysis.json#/classification` and `#/checks` | Direct identity: `ANALYSIS-INVALID`, `record_integrity=false` | VERIFIED | The immutable R387 classifier output is analysis-invalid and supports no scientific result. |
| E-002 | Observations: the full ordered bank was attempted/captured without an execution exception | count/provenance | `formal_execution.json#/trajectory_attempted_count`, `#/trajectory_executed_count`, `#/execution_error`, `#/arms` | Recomputed as 17, 17, null, and 17 exact ordered arms | VERIFIED | All arms were serialized; this does not cure compound-record invalidity. |
| E-003 | Observations/Diagnosis: mapping-order, missing initial evidence, and partial-termination taxonomy cause trace-schema rejection | causal software diagnosis | sealed runner/classifier entries in `formal_seal.json#/sources`; `formal_execution.json#/arms/*/trajectory`; `working/R387_diagnosis.md#Root-causes` | Per-arm subcheck replay finds only trace schema false; exact key/time/termination fields reproduce each defect | VERIFIED | Three instrumentation/taxonomy defects explain the invalid classification. |
| E-004 | Observations: zero arm stays within guards; all 16 nonzero arms cross voltage, with 10 current, 13 apparent-power, six speed, and eight convergence events | numeric diagnostic pattern on invalid data | `formal_execution.json#/arms` | Independently recomputed over stored samples with the sealed limits | QUALIFIED | These are quarantined diagnostic warnings used only to prioritize an unchanged successor gate. |
| E-005 | Conclusions: one integrity-only successor is eligible | decision | `plan.md#Integrity-stopping-and-vulnerability-ledger`, `working/R387_diagnosis.md#Decision-and-green-loop-target` | Scope retains object, bank, thresholds, guards, and no-training boundary | VERIFIED | A separately sealed successor may correct trace evidence/taxonomy only. |

No transformation beyond direct identity/counting is used except E-004. For
E-004, each per-arm guard indicator is the logical OR over stored samples and
devices, followed by a count across the 16 nonzero arms. The evidence source is
invalid for scientific direction, so the qualified wording is mandatory.

## Cross-section drift and unresolved evidence

- No claim-bearing manuscript prose exists for this line, and the feed, claim,
  diagnosis, verdict, programme, line navigation, and route contract all retain
  `ANALYSIS-INVALID` and no-retry language.
- No unresolved artifact prevents the invalidity conclusion: seal, attempt,
  execution, analysis, manifest, sidecars, and sealed source hashes are present.
- A valid signed-authority result is unresolved by design. R387 values cannot
  answer it, and the successor must not treat those values as threshold or
  tuning inputs.

**Evidence decision: PASS for the invalidity-only feed.** This is not a pass
for REGCV1 authority, electrical behavior, or any manuscript claim.

## Power-system domain audit

### Model, units, and intervention

- System boundary is unchanged ANDES 2.0.0 phasor-domain Kundur static network
  with four structurally clean REGCV1 devices; protection, EMT switching,
  hardware, communication, and learning are absent.
- `0.09` system pu on 100 MVA equals 9 MW for `Pref` or 9 Mvar for `Qref` and
  equals 1% of a 900-MVA device rating. The current guard `10 pu` equals
  `(900/100)/0.9`; the apparent-power guard is `900/100=9` system pu.
- Setpoint application occurs after TDS initialization. Requested absolute
  setpoint, applied readback, and achieved `Pe/Qe` trajectories remain distinct.
- The native stored grid starts at its first integration sample; it is not an
  initialization snapshot. This is treated as an evidence defect, not a plant
  response at `t=0`.

### Experiment and inference

- Scientific unit is one fresh independent trajectory arm. The registered bank
  has one zero arm and 16 signed device/channel arms; no stochastic inference
  or uncertainty claim is made.
- Every registered arm is accounted for. Eight native nonconvergences and all
  guard crossings remain visible rather than excluded, but invalidity
  precedence prevents directional or mechanistic inference.
- The zero/nonzero pattern is consistent with an excited unacceptable dynamic
  response under the frozen card, but does not distinguish nonlinear plant
  instability, controller-mode instability, or solver interaction. The feed
  correctly avoids causal physical wording.
- No controller baseline, decoupling metric, modal analysis, robustness bank,
  topology holdout, HIL, or field evidence exists; all such wording stays out.

### Domain findings and boundary table

No BLOCKER, MAJOR, or MINOR finding remains in the invalidity-only wording.

| Proposed statement | Domain status | Evidence-matched boundary |
|---|---|---|
| R387 proves signed authority failure | UNSUPPORTED | R387 is invalid and proves neither pass nor failure. |
| Stored excursions are a serious diagnostic warning | QUALIFIED | Applies only to stored samples in the invalid R387 bank and guides one unchanged correction. |
| The successor may tune the card or reduce the step | UNSUPPORTED | The successor is integrity-only and must retain all scientific fields. |
| The tested object is stable/unsafe | UNSUPPORTED | No valid transient or formal safety conclusion exists. |

**Domain verdict: DOMAIN PASS for the invalidity-only feed.** This does not
constitute a language, citation, venue, or scientific-result pass.

## Smallest ordered repair

1. Preserve R387 and close it analysis-invalid.
2. Register one successor that changes only trace identity, explicit initial
   capture, and advanced-partial-termination classification.
3. Use red-to-green regression fixtures before a new rehearsal/seal.
4. Execute the unchanged 17-arm gate once; accept PASS or STOP only if the new
   compound record passes integrity.
