---
round: R467
state: completed
manuscript_line: yang-md-decoupling-marl
opened: '2026-08-21'
closed: '2026-08-21'
supersedes_rounds:
- R466
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R467 plan — U6 acyclic raw-transport successor

**Opened**: 2026-08-21
**Driver**: Complete the sealed R466 U6 experiment after all physical jobs ran but raw JSON serialization found a cyclic telemetry object.
**Parent**: Preserved engineering-invalid R466 attempt; CLM-1405/R450, CLM-1435/R459, and CLM-1455/R465 remain the scientific parents.

## TL;DR

Reuse the byte-frozen R466 physics, exact-ZOH formulation, scan grid, thresholds,
adaptive bisection, and hardware allocation. Change only the raw segment
serialization so each segment stores an independent snapshot of its row rather
than a reference to the outer row later containing that segment list.

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

- Work class: **evidence successor**; create-only root `results/research_loop/r467_u6_fractional_delay`.
- Preserve the R466 seal and 99 MB partial output byte-for-byte. The R466 physical jobs were not retained after the in-memory serialization failure, so the registered R467 bank must be executed again to produce durable evidence.
- The only implementation correction is `dict(raw)` at segment capture time. Exact ZOH matrices, 201-point `0:0.01:2.0 s` scan, all-pole left/right eigenanalysis, 149-dimensional fixed memory realization, controller, sign convention, endpoint checks, `1e-9` residual threshold, crossing rules, nonlinear 0.95 threshold, parent endpoints, three bisection levels, jobs, seed, disturbances, and guards are unchanged.
- Rehearsal must strict-JSON encode one complete 50-step fractional record and verify that the serialized form can be decoded without object recursion.

### Hardware and launch

- Linear phase: one process with four native numerical threads, as measured in R459.
- Nonlinear phase: 15 workers plus one orchestrator, one native thread each, reusing the R460 rung that was 50.96% faster than eight workers while retaining over 20% WSL memory headroom.
- GPU remains excluded because no CUDA path exists for these small dense eigenproblems or ANDES TDS.
- Commands: `scripts/andes_scratch.py scripts/run_r467_u6_fractional_delay.py rehearse`, then `prepare`, then `run`; retry none.

## Gate

Use exactly the R466 registered pole outcomes and nonlinear outcomes. Publication
entry requires a valid all-pole scan and a valid fractional finite-bank result;
no robust-margin or global-continuity claim is allowed.

## 资产保护契约

Preserve R440/R450/R459/R465/R466, all imported GPT material, and unrelated
dirty changes. Add only the R467 wrapper, lifecycle files, create-only result,
report, claim, feed, verdict, and manifest registrations.

## Cross-references

- R466: preserved cyclic-serialization failure and partial linear output.
- CLM-1405/R450: hashed integer endpoints and phase-delay result.
- CLM-1435/R459: complete Object B model export.
- CLM-1455/R465: fixed-mode complete local model chain.
