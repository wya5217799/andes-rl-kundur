---
round: R342
state: aborted
manuscript_line: icems2026
opened: '2026-08-06'
closed: '2026-08-06'
supersedes_rounds: []
superseded_by_round: null
abort_reason: formal manifest schema mismatch stopped all 16 canary workers before
  physical execution; preserved failure and forbids in-place retry
superseded_note: null
---
# R342 plan — limited-reversal residual mechanism test

**Opened**: 2026-08-06
**Driver**: Test one minimal action-class change after R338 found no neural increment.
**Parent**: CLM-0905 and the user-supplied SELECT-B review.

## TL;DR

Workload: `evidence`. Freeze every R338/R337 object except one number: change
the aligned residual lower bound from `0` to `-0.1`. First prove compatibility
offline. Only after an explicit next gate may five matched seeds train in
parallel; title and old evidence stay unchanged.

## Snapshot at plan-time (oracle as of 2026-08-06)

<!-- Auto-injected by reserve_round.py (F4 audit 2026-05-19). -->
<!-- Do not delete — re-render-render.py STATE.md if you want to -->
<!-- refresh, but keep this block as the plan-time snapshot. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) — verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0090 [opened R341] Can the fresh-qualified predictor support a deterministic physical bridge before any distributed or learning experiment?

## Recently Closed (last 3)

- Q-0089 closed-positive @ R341, by CLM-0900 — Does the selected predictor preserve its registered waveform envelope on an untouched operating-point bank?
- Q-0087 closed-partial @ R339, by CLM-0890 — Which location-dependent input dynamics explain the upstream-load mismatch before any bridge repair?
- Q-0088 closed-negative @ R338, by CLM-0905 — On the fixed four-VSG path, does a neighbour-only distributed edge residual add guarded value beyond the selected causal edge controller and remain non-inferior to a matched joint-observation single actor?

## Methodology

Execute `a=sign(d)*clip(abs(p)+0.5*r,-beta,1)`. Candidate `beta=0.1` is one
user-supplied single point, not a sweep. `beta=0` must be bit-identical to the
current learned controller; `r=0` must recover the classical prior.

Freeze the selected prior, endpoint-only shared actor, critic, reward, R337
development bank, seeds `[421,463,509,557,601]`, 300 x 15 steps, final
checkpoint only, plant, three-edge projection, common inertia, storage and all
guards. Reuse hash-verified R337 beta-zero checkpoints; train only five new
beta-0.1 checkpoints (22,500 new steps). Evaluate classical, five beta-zero and
five beta-0.1 controllers on one new controller-blind 24-case bank. No R338
endpoint may select beta, seeds, bank, thresholds or scheduling.

Stages: (0) focused TDD; (1) same-path no-output rehearsal; (2) five parallel
one-episode smokes, then a mandatory stop for timing/capacity review; (3) five
parallel full trainings; (4) fresh-bank screen; (5) sixteen-worker 15-step
concurrency canary, then a mandatory stop; (6) sixteen-shard formal run.
Persist every episode monitor, worker log and trajectory immediately. Any
pre-formal failure stops without retry; formal failures remain in analysis.

## Gate

Offline gate: beta-zero exact parity, classical nesting, reverse magnitude no
larger than 0.1, zero-severity zero action, NumPy/tensor parity and old
checkpoint load. Any failure blocks ANDES.

Formal success requires beta-0.1 to improve both primary means by at least 2%
versus classical, improve both versus paired beta-zero, put every paired 95%
interval upper bound below zero, improve both endpoints in at least 3/5 seeds,
and pass the unchanged +5% tail and physical guards. No reverse use is
`NO-MECHANISM-ENGAGEMENT`; otherwise classify the first bounded negative gate.
Stop after this beta and bank; no tuning or redraw.

### Outcomes

- All registered efficacy and guard thresholds pass:
  `LIMITED-REVERSAL-INCREMENT`.
- Classical gate fails: `NO-CLASSICAL-INCREMENT`.
- Classical passes but paired beta-zero gate fails:
  `NO-BETA-ZERO-INCREMENT`.
- Efficacy passes but tail/physical guard fails:
  `LIMITED-REVERSAL-GUARD-FAIL`.
- Integrity or mechanism-engagement gate fails: use that earlier bounded
  classification and interpret no broader learned-control claim.

The measured beta-zero baselines are the five R337 runs
`distributed_prior_s421`, `distributed_prior_s463`,
`distributed_prior_s509`, `distributed_prior_s557`, and
`distributed_prior_s601`; no cross-run estimate replaces them.

## Formal launch contract

- formal_entry: `python scripts/run_r342_limited_reverse_residual.py execute`
- continuation_entry: `python scripts/run_r342_limited_reverse_residual.py continue-through-canary`
- formal_release_entry: `python scripts/run_r342_limited_reverse_residual.py execute-formal`
- rehearsal_command: `/home/wya/andes_venv/bin/python scripts/andes_scratch.py scripts/run_r342_limited_reverse_residual.py rehearse`
- rehearsal_record: `memory/rounds/R342/rehearsal_v2.json`
- rehearsal_v1_note: the preserved `rehearsal.json` exposed a self-referential
  source-list instrumentation defect before any attempt, seal, training, or
  physical trajectory existed; it is not an experimental retry.
- rehearsal_scope: same-pre-attempt-path; no formal attempt or output
- rehearsal_checks: source_hash,parent_hash,installed_package,installed_case,output_absence
- wsl_python_processes: 16
- native_threads_per_process: 1
- capacity_evidence: `memory/rounds/R342/host_capacity.json`
- host_process_budget: 16
- other_reserved_processes: 0

Readiness is `MEASURE-FIRST`: focused tests and five-way smoke precede the
22,500-step run, and `execute` stops at that smoke gate. Full training needs a
separate continuation command after reviewing measured timing. Training uses
five workers because seeds are indivisible; screen/formal may use sixteen.
ANDES is CPU-bound; the 4,929-parameter actor does not justify changing the
established CPU path to GPU. The physical canary is a second mandatory stop
before any formal controller outcomes are generated.

## 资产保护契约

标题、R338 全部产物和结论不改。只允许为 beta 默认零的兼容契约、动态并发预算、
R342 入口/判定和聚焦测试做必要改动。新数据只写 `memory/rounds/R342` 与
`results/r342_*`；publication gate 前不改论文正文或既有 claim。

## Cross-references

- `memory/claims/CLM-0905.md`
- `paper/icems2026/reports/R338.md`
- `paper/icems2026/working/gpt_pro_minimal_change_algorithm_optimization.md`
- `memory/rounds/R337/training_seal.json`
- `memory/rounds/R339/host_capacity.json`
