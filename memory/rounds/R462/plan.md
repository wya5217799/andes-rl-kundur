---
round: R462
state: aborted
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: post-run audit found nested empty guard-multiplier placeholder dicts
  were misclassified as recorded constraint data; preserve sealed result and correct
  only in successor
superseded_note: null
---
# R462 plan — U4 JSON-safe successor to the preserved R461 attempt

**Opened**: 2026-08-21
**Driver**: Complete the already-rehearsed U4 audit after R461 correctly assigned positive infinity to invalid candidates but failed to encode that state in strict JSON.
**Parent**: R461 aborted engineering attempt; CLM-1440/R460, CLM-1390/R452, and CLM-1420/R456 remain the scientific parents.

## TL;DR

Reuse the byte-frozen R461 computation without changing any equation or candidate ordering. Change only the output encoding: non-finite guard residuals become JSON `null` plus an explicit `positive_infinity` status and named non-finite guard list. A read-only checker reconstructs infinity from that status and independently reproduces the winner.

## Snapshot at plan-time (oracle as of 2026-08-21)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0112 [opened R445] Does the finite-bank information-level margin program (shared action variables per non-anticipative info class, solution section 5.4) certify or refute INFORMATION-LIMITED for the 2% joint target under the exact R352/R353 observation histories?

## Recently Closed (last 3)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0111 closed-negative @ R397, by CLM-1130 — Do one-device-at-a-time signed Pref and Qref steps on the two-unit PPVSM1 diagnostic cell produce correctly applied, signed, target-attributed active and reactive power responses without solver or electrical-guard failure, thereby opening only a separately registered droop-slope matching verification?

## Methodology

### Classification and single-factor correction

- Work class: **evidence successor**; create-only root `results/research_loop/r462_u4_guard_audit`.
- Preserve the R461 seal, source, rehearsal, and partial output byte-for-byte.
- Scientific inputs, metrics, guard thresholds, 350-candidate class, and exact enumeration are identical to the R461 plan.
- The only correction is serialization of mathematically positive-infinite residuals for invalid candidate rows. Each such numeric value is encoded as `null`; `t_status` and residual-status maps state `positive_infinity`. Finite values remain exact JSON numbers.
- The independent checker reads only the emitted JSONL, restores positive infinity from status fields, verifies all 350 IDs, recomputes the minimum, active guards, runner-up margin, and compares them with the result summary.

### Capacity and launch

- Static dependency-ordered reduction: one process, one native thread; no ANDES run and no duplicate scientific job.
- Rehearsal must exercise the strict JSON encoder in memory and confirm no non-standard token is emitted.
- Commands: `python scripts/run_r462_u4_guard_audit.py rehearse`, then `prepare`, then `run`.
- Retry policy: none; preserve a terminal attempt.

## Gate

`U4-GUARD-AUDIT-VALID` requires every unchanged R461 scientific check plus valid strict JSON and independent reconstruction of the exact phase-I result. Otherwise use `U4-GUARD-AUDIT-INVALID` or `ENGINEERING-INVALID` as defined in R461.

## 资产保护契约

R431/R452/R456/R458/R459/R460 and the full R461 attempt remain immutable. Add only the R462 wrapper, round records, create-only formal output, feed, claim, and registrations.

## Cross-references

- R461: preserved serializer failure; no scientific verdict.
- CLM-1440 / R460: raw trajectory bank.
- CLM-1390 / R452: 350-schedule finite bank.
- CLM-1420 / R456: bounded post-hoc multiplier diagnostic.
