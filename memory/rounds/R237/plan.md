---
round: R237
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R237 plan — phi_f=0 (disable load-step penalty; final paper reward term ablation)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, last reward term test)
**Driver**: R236 showed phi_h/phi_d are inert at V4 magnitudes. R237
tests the last untested paper reward term: phi_f (load-step penalty,
default 100). If SOTA at phi_f=0, then **phi_abs is the SOLE
load-bearing reward** (and that term isn't even in paper). If
collapse, phi_f is the only paper term that contributes.
**Parent**: R236 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-f 0 (disable
load-step penalty entirely). Two outcomes:
- **SOTA (geo ≥ 0.40)**: phi_abs is the sole load-bearing reward;
  ALL paper Eq.14 terms are effectively inert on V4 ANDES.
  Strongest possible paper-integrity finding.
- **REGRESS (geo < 0.30)**: phi_f is necessary; reward is two-term
  {phi_abs, phi_f}; paper-faithful phi_f at least is preserved.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-f 0 \
    --save-dir results/r237_w1_hreg_phif0_s54
```

## Cross-references

- R236 (phi_h/phi_d=0 SOTA)
- R214 (phi_abs=0 collapse)
- R218 (paper-strict collapse)
- v4_config.py phi_f docstring
