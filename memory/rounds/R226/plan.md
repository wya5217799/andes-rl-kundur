---
round: R226
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R226 plan — SOTA hyper at --vsg-m0 350 (1.75× inertia, narrow cliff)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, cliff location)
**Driver**: Breakdown cliff is in (1.5×, 2×]. R226 = 1.75× bisects.
**Parent**: R225 (1.5× robust), R224 (2× fragile).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --vsg-m0 350. Two outcomes:
- **STILL VIABLE (geo ≥ 0.35)**: cliff in (1.75×, 2×]; safe window
  extends to 1.75×.
- **BREAKDOWN (geo < 0.30)**: cliff in (1.5×, 1.75×]; narrow window.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-m0 350 \
    --save-dir results/r226_w1_hreg_m0_350_s54
```

## Cross-references

- R225 (1.5× = 0.4031)
- R224 (2× = 0.2753)
- R201 (trained 1× = 0.4152)
