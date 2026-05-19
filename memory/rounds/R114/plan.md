---
round: R114
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R114 plan — Toggler-OFF retrain (test CLM-0194 hypothesis, train better agent)

**Status**: ABANDONED — driver hypothesis falsified by CLM-0215 before launch
**Opened**: 2026-05-19
**Abandoned**: 2026-05-19 (same day)
**Driver (DEAD)**: PI "训练更好 agent". Leveraged CLM-0194 (R110) Toggler
finding. **Falsified by CLM-0215 (R113)**: Toggler net effect on max_df
is +0.9 % average (LS1 -8.8 %, LS2 +10.5 %), not the 30 %+ that would
make Toggler-OFF retrain a worthwhile attempt at breaking 0.391.
**Parent**: CLM-0094 R72_w4 SOTA + CLM-0194 R110 Toggler finding +
CLM-0144 91-round algo plateau + **CLM-0215 (closes the driver)**.

## Why abandoned (not just deferred)

The decision rule from this plan's gate section was:
- geo ≥ 0.45 ⇒ plateau Toggler-induced
- geo ∈ [0.35, 0.42] ⇒ Toggler-OFF doesn't help RL
- geo < 0.35 ⇒ over-fit to compound disturbance

CLM-0215 measured the Toggler-OFF *physics* effect directly (zero-action,
both LS scenarios): the average |Δf| peak moves by **less than 1 %**.
A 75-episode RL retrain on a system that differs by < 1 % cannot
plausibly produce a +15 % geo lift (0.391 → 0.45). The most likely
outcomes under the rule above are now:
- geo ≈ 0.39 ± noise: re-confirms 91-round plateau (already known)
- geo < 0.35: re-confirms RL training stochasticity (already known)

Neither outcome would close any *open* question. Cost (≈ 25 min WSL +
1 ckpt slot + R102/R103/R100 contention) > information value.

## What would re-open R114-equivalent

If CLM-0215 mechanism interpretation turns out wrong (LS1 -8.8 % and
LS2 +10.5 % do not *actually* cancel for the trained policy because
its non-linear response amplifies one direction), then a focused
**eval-only** retest would resurrect: run R72_w4 SOTA ckpt on
Toggler-OFF env (no retrain) and compare LS1+LS2 geo. That's ~3 min
wall, much cheaper than retrain. Open a new Q if you want it.

## Resource handoff

The 1 WSL slot reserved for R114 returns to the pool. Active in-flight
candidates that may use it next: R102 (magnitude-PI grid, Q-0023
still open) is the highest-ROI follow-up — close Q-0023 before any
new plateau-attack round.

## Cross-references

- CLM-0094 R72_w4 SOTA (geo 0.391, training baseline)
- CLM-0144 91-round algo plateau
- CLM-0194 R110 Toggler finding (audit, audit-level claim)
- **CLM-0215 R113 Toggler ablation** (quantitative test, closes the
  R110 hypothesis as NEGATIVE)
- Q-0025 closed-negative @ R113 by CLM-0215
- R08 §2 Finding 2 (2× max_df residual — NOT explained by Toggler;
  cause remains open. Likely F2 load topology + F3 capacitive q +
  D₀-heterogeneity per R89 follow-ups; opened CLM-0173 thread.)
- R85 / CLM-0184 (classical baseline droop 0.197 — unaffected,
  doesn't read DISABLE_TOGGLER)
