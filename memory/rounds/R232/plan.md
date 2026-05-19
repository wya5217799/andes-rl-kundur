---
round: R232
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R232 plan — phi_h=0.01 (1.8× V4 default, narrow phi_h sweet spot)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, phi_h cliff bracketing)
**Driver**: R231 (phi_h=0.05 = 10× V4) collapsed. Narrow the cliff:
phi_h=0.01 (1.8× V4). If viable, sweet spot extends; if collapse,
sweet spot is tight around V4 default 0.0056.
**Parent**: R231 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0.01 --phi-d 0.01.
Two outcomes:
- **VIABLE (geo ≥ 0.30)**: sweet spot in [0.006, 0.05) range; cliff
  between 0.01 and 0.05.
- **COLLAPSE (geo < 0.10)**: sweet spot is tight (≤0.01); even 1.8×
  V4 default breaks.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0.01 --phi-d 0.01 \
    --save-dir results/r232_w1_hreg_phih01_s54
```

## Cross-references

- R201 (V4 phi_h=0.0056 SOTA)
- R231 (phi_h=0.05 collapse)
- R218 (paper phi_h=1 collapse)
