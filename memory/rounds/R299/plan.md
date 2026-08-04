---
round: R299
state: completed
opened: '2026-08-03'
closed: '2026-08-03'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R299 plan — edge-local information-value sentinel

**Opened**: 2026-08-03
**Driver**: Kill or justify adaptive distributed learning after the strong
R298 classical residual, before spending compute on neural training.
**Parent**: Q-0056; CLM-0700.

## TL;DR

Run one 24-trace development sentinel around the frozen R298 controller. An
outcome-seeing edge library measures only an upper bound; learning remains
blocked unless the oracle beats the best fixed arm and early edge-local
measurements explain which edge benefits.

## Snapshot at plan-time (oracle as of 2026-08-03)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0056 [opened R299] Does the R298 residual-DAPI baseline leave material, locally signalled edge-allocation headroom for a deployable distributed residual?

## Recently Closed (last 3)

- Q-0055 closed-positive @ R298, by CLM-0700 — Does the selected zero-sum relative-RoCoF DAPI residual retain held-out fast inter-area value against fresh DAPI and centralized vector PI?
- Q-0054 closed-positive @ R297, by CLM-0695 — Does a full anchor-magnitude zero-sum relative-RoCoF residual cross the materiality gate that the half-magnitude boundary arm narrowly missed?
- Q-0053 closed-negative @ R296, by CLM-0690 — Can a zero-sum neighbour-relative RoCoF residual materially improve the fast inter-area response of explicit distributed DAPI without common harm?

## Methodology

Freeze the R298 explicit local residual DAPI as base. Let filtered RoCoF be
`r_i`, ring degree be `d=2`, and the established full-anchor gain be `Kv`.
The base residual is `u_i=-Kv/d sum_j(r_i-r_j)`. A candidate edge increment
on undirected edge `(i,j)` is
`du_i=-Kv/d(r_i-r_j)`, `du_j=-du_i`; therefore its pre-projection sum is
exactly zero and it uses only the two incident measurements. Equal increments
on all four ring edges are exactly the fixed `2Kv` comparator.

Use four sentinel cases already released from R298 formal use and now treated
as development only: `k1.25/PQ_0/negative`, `k1.25/PQ_1/positive`,
`k1.75/PQ_Bus15/negative`, and `k1.75/PQ_0/positive`. Freshly run six arms per
case: base `Kv`, fixed all-edge `2Kv`, and one extra-gain arm for each of ring
edges `(0,1)`, `(1,2)`, `(2,3)`, `(0,3)`. All 24 jobs use 100 steps at 0.2 s,
the same plant, slow DAPI state, four ESD1 action coordinates, projection,
limits and physical endpoints.

For each case, exclude any candidate that violates completion, finite telemetry,
storage/action/physical guards, a common-endpoint ratio of 1.05, or pre-
projection zero-sum error `1e-12`. Among feasible arms, an explicitly outcome-
seeing oracle minimizes the maximum of fast-inter-area-IAE and synchronization-
loss ratios. The best fixed arm minimizes the same aggregate criterion with one
arm used for every case. Early causal edge features use only the first five
post-reset samples of the two incident frequencies and reconstructed filtered
RoCoF; outcome data never enter those features.

The disjoint full-eval bank is frozen now, before sentinel outcomes:
`tie k={1.375,1.625} x location={PQ_0,PQ_Bus14,PQ_Bus15} x sign={-1,+1}`.
It may be opened only after a separately developed causal controller passes;
R299 itself cannot consume it.

## Comparison-identifiability gate

- Fixed arms share physical actions, information, timing, limits, execution,
  tuning count and endpoints; only the frozen edge-gain placement differs.
- The per-case oracle has future outcome information. It identifies optimistic
  adaptive-allocation headroom only, never deployable efficacy.
- `ALLOW` fixed-arm and best-fixed contrasts; `QUALIFY` the oracle upper bound;
  `BLOCK` MARL, neural, multi-network-versus-single-network and architecture-
  class claims. A future network comparison remains blocked until action space,
  deployment information, capacity, optimization, interaction/tuning budget,
  seeds and evaluation data are prospectively matched.

## Gate

Validity precedes endpoints. If any of 24 records/sidecars or registered guards
fails, classify `INVALID` and do not interpret performance.

- `NO-ADAPTIVE-EDGE-VALUE`: oracle does not improve both differential endpoints
  over best fixed, or either aggregate oracle/best-fixed ratio exceeds `0.99`.
- `CLASSICAL-RETUNE`: one fixed non-baseline arm supplies the material gain and
  oracle/best-fixed does not clear the 1% joint margin.
- `OUTCOME-ONLY-EDGE-GAP`: oracle clears both 1% margins and selects at least two
  edge arms, but pooled early-local feature versus marginal-benefit Spearman is
  below `0.5` or the largest-feature edge matches the best edge in fewer than
  three of four cases.
- `LOCALLY-SIGNALLED-EDGE-GAP`: oracle clears both 1% margins, selects at least
  two edge arms, Spearman is at least `0.5`, best-edge match is at least 3/4,
  and every common/physical/zero-sum guard passes.

Only the last class authorizes a new causal distributed-controller development
round. None authorizes neural training or formal performance claims directly.

## 资产保护契约

- R274--R298 plans, seals, traces, summaries, feeds, claims and verdicts stay
  byte-for-byte unchanged.
- Add Q-0056/R299 state, one reusable edge-increment controller seam, one stable
  runner, focused tests, one seal and create-only JSON records/summary with
  sidecars. No manuscript file changes.
- Use at most three scratch-isolated WSL Python workers. Do not inspect endpoint
  results until all sentinel jobs and sidecars are complete.

## Cross-references

- CLM-0700 is the frozen strong classical baseline and claim ceiling.
- Measured baseline source: `results/r298_relative_rocof_formal`.
- The future eval bank is prospective navigation only; it is not R299 evidence.
- Execution amendment: the first pre-trace smoke found absent arm metadata
  required by the reused runner. The original seal remains immutable; v2 adds
  only explicit fixed `sync_gain`/`consensus_gain`, records zero retained traces,
  and leaves controller, matrix, estimand, thresholds and future bank unchanged.
