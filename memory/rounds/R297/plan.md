---
round: R297
state: completed
opened: '2026-08-02'
closed: '2026-08-02'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R297 plan -- final relative-RoCoF amplitude adequacy check

**Opened**: 2026-08-02
**Driver**: Resolve whether R296's boundary failure reflects insufficient
residual amplitude or structural saturation, with one final gain only.
**Parent**: Q-0054; CLM-0690.

## TL;DR

Freshly compare `Kv=0` with `Kv=1/|H(jw*)|=0.2442407 system-pu*s/Hz`, equal
to the frozen static synchronizing-action magnitude at the 1.135 Hz anchor.
Run eight trajectories in three shards. Reuse every R296 gate unchanged. Pass
opens a separate full evaluation; fail permanently ends this gain direction.

## Snapshot at plan-time (oracle as of 2026-08-02)

<!-- Auto-injected by reserve_round.py; preserve as plan-time navigation. -->

## Open Questions

- Q-0004 [opened R46] AndesBaseEnv absorb-into-V4 (complete AD-01) -- verify 1e-9 bit-identical from WSL before landing
- Q-0026 [opened R260] Will the Archive Index actually be queried (lazy-extraction loop signal)?
- Q-0054 [opened R297] Does a full anchor-magnitude zero-sum relative-RoCoF residual cross the materiality gate that the half-magnitude boundary arm narrowly missed?

## Recently Closed (last 3)

- Q-0053 closed-negative @ R296, by CLM-0690 -- relative-RoCoF boundary no-go.
- Q-0052 closed-negative @ R295, by CLM-0685 -- consensus-time-scale no-go.
- Q-0051 closed-partial @ R294, by CLM-0680 -- model-first distributed baseline.

## Methodology

Reuse R296's explicit local controller, causal `tau=0.2 s` RoCoF filter,
regular ring, four independent ESD1 actions, DAPI gains, storage projection,
100-step horizon, four outcome-aware cases, endpoints, and validity guards.
All arms compute the same state. Sole treatment is
`Kv in {0,1/4.0943215}={0,0.2442407} system-pu*s/Hz`.

The comparator matrix is fully matched in sensors/history, action, execution,
plant, cases, horizon and compute class. The contrast identifies only the
executed full-amplitude residual on this development bank. It cannot identify
architecture, MARL, topology, robustness, stability, safety, or deployment
effects.

## Gate

All eight jobs must complete with finite telemetry, 100 mechanism samples,
valid TDS/exit, zero storage violations, vector actions, and pre-projection
residual-sum error at most `1e-12`. The candidate passes only if fast
inter-area IAE ratio is at most `0.99`, synchronization-loss ratio at most
`1.01`, every common mean ratio at most `1.05`, worst individual common ratio
at most `1.10`, and residual RMS is nonzero. No threshold or arm may change
after seal.

## Predeclared full-evaluation return gate

If and only if R297 passes, a new round will freeze the disjoint 12-case bank
`tie k={1.25,1.75} x location={PQ_0,PQ_1,PQ_Bus15} x sign={-1,+1}` before
any trajectory. It must freshly run baseline DAPI, selected residual DAPI, and
centralized vector PI, retain paired uncertainty and all failure/physical
guards, and keep central/distributed wording at the executed-formulation level.
If R297 fails, this evaluation is cancelled.

## Asset preservation contract

- Preserve all R274--R296 sealed artifacts and prose byte-for-byte.
- Add Q-0054/R297 state, one runner, focused tests, one JSON seal, and
  create-only results with sidecars; no extra round Markdown.
- Use `andes_scratch.py`; do not edit controller source, manuscripts, rewards,
  or neural code.

## Cross-references

- CLM-0690: half-amplitude fast-IAE ratio 0.990029 with all other gates passed;
  exact result remains a failure.
