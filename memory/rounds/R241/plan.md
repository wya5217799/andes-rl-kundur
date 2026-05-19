---
round: R241
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R241 plan — hreg + only phi_abs at s51 (cross-seed verify paper-Eq.14-inertness)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, paper-integrity cross-seed)
**Driver**: R238 (hreg + only phi_abs at s54) = 0.4128. R241 verifies
at s51 — if also near hreg-s51 baseline, paper-Eq.14-inertness is
cross-seed universal.
**Parent**: R238 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s51 with --phi-h 0 --phi-d 0
--phi-f 0. Compare to:
- R203 (s51, full reward, hreg): 0.3901 baseline
- Expected if paper-terms inert: ~0.39 ± noise

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 51 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r241_w1_hreg_onlyphiabs_s51
```

## Cross-references

- R238 (s54 hreg + only phi_abs = 0.4128)
- R203 (s51 hreg full reward = 0.3901)
- R239 (s54 scalar + only phi_abs = 0.3954)
