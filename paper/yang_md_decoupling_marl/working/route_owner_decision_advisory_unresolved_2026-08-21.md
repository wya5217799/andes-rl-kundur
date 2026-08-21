# Owner decision: resolve the advisory's unresolved items (2026-08-21)

## Decision

The repository owner directed "解决全部 / 长任务 / 提高cpu效率" on
2026-08-21: execute the items left unresolved by the VSG failure-math
advisory (`working/vsg_failure_math_advisory_20260820/`), not just archive
them. The advisory's three-way intake (IMPORT_NOTE.md) verified its algebra
(probe 8/8) but left the empirical instantiations and causal attributions
open. This registers that directive as the line's forward work anchor,
extending the soft-spot program's scope with a journal-extension
measurement/certificate program.

## Scope of the authorized program

| id | item | kind | status |
|---|---|---|---|
| C1 | FIR-Youla/SLS controller-class certificate | offline math (scratch) | DONE (offline construction): conditional program, no instantiated certificate |
| P3 | DAE first-order authority B_{u,r} (symbolic + finite-difference) | offline analysis + ANDES eval measurement | DONE: B_{u,r}=0 structural + measured (R446/CLM-1390, all 8 columns exactly 0) |
| P1 | relaxed-block complex response + matched finite difference | ANDES eval measurement | DONE (R447/CLM-1395): G_K/G_L export seam validated (ratio 0.9065 vs R408 0.938); P1.1 d/drho decomposition deferred |
| P2 | same-bank integer-delay sweep + loop export | ANDES eval measurement | design done (same note); loop-break L_0 needs a sealed design decision |
| M3/M5/M4/M1/M2 | causal mechanism experiments | ANDES training/eval | queued (journal extension) |

Priority: offline items first (C1, P3 symbolic), then ANDES eval measurements
(P3 -> P1 -> P2), then M causal training last. Order is the advisory brief's
intake contract priority (P1, P2, P3 first; then M3, M5, M4, M1, M2; then C1),
re-sequenced so the offline/cheap items land first.

## Governance (inherited from the soft-spot program, not restated)

- Each item that needs physical execution opens its own evidence round on this
  line, one active round at a time: reserve -> plan -> preflight -> capacity
  -> rehearsal -> seal -> execute -> feed -> claim -> gate -> close.
- saturate-or-skip parallelism: eval records ~12 s serial; training ~2.4 h.
  <= 20 min -> single-process seam; > 20 min or training -> measure the
  capacity ladder (rungs 1/2/4/8/12/16) first, then run at the sealed rung,
  native threads 1, `other_reserved_processes` 0.
- Every mechanism prediction carries the advisory's observable matrix
  (`vsg_failure_math_advisory_20260820/verification/m_observable_matrix.md`)
  into the round plan's `## Theory intake`; run
  `external_theory_intake_lint.py R<N>` before close.
- The ICEMS 2026 submission path outranks this program: after 2026-08-28
  registration, only results whose full lifecycle completes before the
  2026-09-07 final-paper freeze may enter the manuscript; everything else
  feeds the post-conference extension and must stay out of the paper.

## Authority boundaries

- No title change; no algorithm-dimension sweep (R86 plateau); no
  cross-simulator 1:1 chase (ADR-0005); no bigger-than-Kundur grids.
- P3/P1/P2 are measurements of the frozen ANDES object, not learner changes;
  M items that touch the learner need new rounds with their own seals and
  single-factor contracts.
- Topology/EIG hard gate (CLM-0665) applies to any variant work.
- External answers stay design aids: no number enters the manuscript before
  repo-side verification (the external-theory-intake contract).

## Records

- Decision doc: this file
- Advisory disposition: `working/vsg_failure_math_advisory_20260820/IMPORT_NOTE.md`
- Advisory index: `memory/notes/NOTE-0031.md`
- Problem registry: `memory/tools/gpt_pro_manifest.json` (all 9 brief items
  marked answered; unresolved empirical parts tracked here, not re-sent)
- Future rounds: reserved by the atomic tool when each item starts (R446+)
