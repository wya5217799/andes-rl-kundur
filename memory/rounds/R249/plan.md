---
round: R249
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R249 plan — hreg + only phi_abs at s50 (3rd seed for hreg paper-inertness)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, 3rd seed verify hreg-inertness)
**Driver**: hreg+only-phi_abs verified at s54 (R238) and s51 (R241).
R249 adds s50 to complete 3-seed picture for hreg's paper-Eq.14
universality.
**Parent**: R238, R241.

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s50 with --phi-h 0 --phi-d 0
--phi-f 0. Expected (based on hreg-inertness pattern): geo ≈ 0.35
(matches R185 full-reward s50 baseline).

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r249_w1_hreg_onlyphiabs_s50
```

## Cross-references

- R238 (s54), R241 (s51) — paper-inertness verified
- R185 (hreg full reward s50 = 0.3515 baseline)
