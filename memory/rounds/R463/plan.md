---
round: R463
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R463 plan — U4 recursive empty-ledger correction

**Opened**: 2026-08-21
**Driver**: Correct R462's post-run discovery that a dictionary containing only empty trace arrays is a schema placeholder, not recorded constraint data.
**Parent**: R462 aborted semantic-export attempt; unchanged scientific parents CLM-1440/R460, CLM-1390/R452, and CLM-1420/R456.

## TL;DR

Reuse the byte-frozen R462 metric, strict-JSON, and phase-I computations. Recursively classify a training constraint field as recorded only when it contains at least one actual leaf datum. Export field-level availability for every arm×seed ledger and require all 15 R431 ledgers to be reported truthfully.

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

- Work class: **evidence successor**; create-only root `results/research_loop/r463_u4_guard_audit`.
- Preserve R461 and R462 plans, seals, sources, partial/formal outputs, and abort records byte-for-byte.
- Metric equations, 24 raw trajectories, R456 30-cell export, 350-schedule class, thresholds, strict JSON encoding, and exact-enumeration result are unchanged.
- Replace only the ledger-presence predicate: lists are recorded only if non-empty; dictionaries are recorded only if some recursively nested value is recorded; `null` and empty containers are not data.
- Emit per-field statuses for `episode_common_costs`, `lagrange_trace`, and `guard_multipliers`, plus an overall ledger status. A checker independently reads the 15 source manifests and repeats the recursive predicate.

### Capacity and launch

One process and one native thread; deterministic static reduction, no ANDES run, no duplicate job. Commands are `python scripts/run_r463_u4_guard_audit.py rehearse`, then `prepare`, then `run`. No retry or overwrite.

## Gate

`U4-GUARD-AUDIT-VALID` requires all unchanged R462 scientific/JSON checks, exact phase-I reconstruction, 15 separate R431 ledgers, and exact agreement between exported and independently recomputed field availability. Any disagreement is invalid.

## 资产保护契约

Preserve all earlier rounds and imported material. Add only R463 wrapper/ledger records, create-only output, feed, claim, and registrations.

## Cross-references

- R462: preserved strict-JSON result with invalid ledger-presence count; not publication evidence.
- CLM-1440 / R460; CLM-1390 / R452; CLM-1420 / R456.
