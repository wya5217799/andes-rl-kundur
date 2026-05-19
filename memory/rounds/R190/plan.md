---
round: R190
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R190 plan — control: td3_lstm scalar at s49 + seed-offset=100 (isolate env-side mechanism)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, control experiment for R188 env-side mechanism)
**Driver**: R188 (hreg + offset) gave geo 0.2032 at s49 — much better
than s49 with offset=0 (0.046). Question: does offset alone rescue,
or is hreg + offset the joint rescue? R190 = R72_w4 scalar critic
(no hreg) at s49 with seed-offset=100. Cleanest isolation.
**Parent**: R188 verdict, CLM-0350.

## TL;DR

Train `td3_lstm` (scalar critic, no hreg) at s49 with seed-offset=100,
75ep. Two outcomes:

- **RESCUED (geo > 0.10, LS1 > 0)**: env/replay-side mechanism is the
  **sole** cause of s49 collapse; hreg is irrelevant to s49.
- **STILL COLLAPSE (LS1=0, geo < 0.10)**: hreg + offset is the joint
  rescue; offset alone is insufficient. Mechanism is composite.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 49 --seed-offset 100 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r190_w1_scalar_s49_offset100
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R188 verdict (env-side mechanism confirmation)
- CLM-0350 (Q-0005 closed-partial)
- CLM-0345 (hreg-doesn't-rescue-s49 at offset=0)
