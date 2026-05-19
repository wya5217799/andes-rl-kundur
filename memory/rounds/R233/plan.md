---
round: R233
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R233 plan — phi_h=0.02 (3.6× V4, bisect phi_h cliff)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, phi_h cliff)
**Driver**: R232 (1.8×) viable, R231 (9×) collapse. R233 bisects.
**Parent**: R232 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0.02 --phi-d 0.02
(3.6× V4 default). Two outcomes:
- VIABLE (geo ≥ 0.30): cliff in (0.02, 0.05]; sweet spot extends
- COLLAPSE (geo < 0.10): cliff in (0.01, 0.02]; tight sweet spot

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0.02 --phi-d 0.02 \
    --save-dir results/r233_w1_hreg_phih02_s54
```

## Cross-references

- R231 (phi_h=0.05 collapse)
- R232 (phi_h=0.01 SOTA)
- R201 (phi_h=0.006 SOTA)
