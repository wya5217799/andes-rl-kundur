---
round: R229
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R229 plan — SOTA hyper at gamma=0.95 (short-term discount, complementary to R213)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, complete gamma sweep)
**Driver**: R213 (gamma=0.999) gave bit-identical SOTA. Now try the
OPPOSITE end: gamma=0.95 (low discount, short-term focus). Could
shift actor toward LS1 (fast recovery) at LS2 cost — finding a
different basin.
**Parent**: R201 (default gamma=0.99), R213 (gamma=0.999 = identical).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --gamma 0.95. Three
outcomes:
- **DIFFERENT POLICY (LS1/LS2 shifted from R201)**: low gamma finds
  different basin; characterize tradeoff curve.
- **BIT-IDENTICAL**: gamma genuinely doesn't matter in [0.95, 0.999]
  range; reward landscape is gamma-invariant at this horizon.
- **REGRESS**: low gamma destabilizes; gamma=0.99 is intentional.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --gamma 0.95 \
    --save-dir results/r229_w1_hreg_gamma095_s54
```

## Cross-references

- R201 (gamma=0.99 SOTA)
- R213 (gamma=0.999 bit-identical)
