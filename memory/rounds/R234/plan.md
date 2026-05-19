---
round: R234
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R234 plan — phi_h=0.003 (half V4 default, test LOW side of sweet spot)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, phi_h low side)
**Driver**: phi_h high-side cliff narrowed to (0.01, 0.02]. Test LOW
side to characterize sweet spot width.
**Parent**: R201, R232, R233.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0.003 --phi-d 0.003
(half V4 default 0.0056). Two outcomes:
- VIABLE (geo ≥ 0.30): sweet spot extends down; full range is at
  least [0.003, 0.01]
- COLLAPSE (geo < 0.10): sweet spot is narrow around V4 default

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0.003 --phi-d 0.003 \
    --save-dir results/r234_w1_hreg_phih003_s54
```

## Cross-references

- R201 (V4 phi_h=0.0056 SOTA)
- R232 (phi_h=0.01 SOTA, +1.8×)
- R233 (phi_h=0.02 collapse, +3.6×)
