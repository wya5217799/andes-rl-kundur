---
round: R236
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R236 plan — phi_h=0.0 (disable frequency-deviation penalty entirely)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, phi_h=0 limit)
**Driver**: phi_h sweet spot extends arbitrarily low (R235 viable at
0.001). Test extreme limit: phi_h=0 (disabled entirely). If SOTA,
phi_h is genuinely unnecessary for training — the V4 reward landscape
trains on phi_abs + phi_f alone. **Major paper finding**: paper Eq.14
phi_h term is not contributing.
**Parent**: R235 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0 --phi-d 0. Two
outcomes:
- **SOTA (geo ≥ 0.40)**: phi_h is unnecessary. Reward landscape needs
  only phi_abs + phi_f. **Major paper finding** for reward-shaping
  reproducibility.
- **REGRESS / COLLAPSE (geo < 0.30)**: phi_h provides necessary
  gradient even at very small magnitudes; the sweet spot has a
  minimum (≥0.001).

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0 --phi-d 0 \
    --save-dir results/r236_w1_hreg_phih0_s54
```

## Cross-references

- R235 (phi_h=0.001 SOTA)
- R201 (V4 phi_h=0.0056 SOTA)
- R234 (phi_h=0.003 SOTA)
