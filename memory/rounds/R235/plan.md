---
round: R235
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R235 plan — phi_h=0.001 (0.18× V4, find LOW-side cliff)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, phi_h low cliff)
**Driver**: phi_h sweet spot extends to 0.003 (R234). R235 = 0.001
(0.18× V4) tests very low end. If viable, sweet spot is wide on low
side; if collapse, low cliff is in (0.001, 0.003].
**Parent**: R234 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0.001 --phi-d 0.001.
Outcomes:
- VIABLE (geo ≥ 0.30): low side is wide; sweet spot ≥ [0.001, 0.01]
- COLLAPSE (geo < 0.10): low cliff in (0.001, 0.003]

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0.001 --phi-d 0.001 \
    --save-dir results/r235_w1_hreg_phih001_s54
```

## Cross-references

- R234 (phi_h=0.003 SOTA-equivalent)
- R201 (V4 0.006 SOTA)
