---
round: R248
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R248 plan — scalar s50 with paper-original phi_h=1, phi_d=1 + phi_abs=50 (paper-faithful+patch for scalar)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, scalar paper-rescue test)
**Driver**: R246 (parallel) found scalar+only phi_abs at s50 = 0.2346,
-28% from baseline. Scalar needs paper terms at non-s54 seeds. R248
tests if FULL paper-strict weights (phi_h=phi_d=1) + phi_abs=50
rescues scalar at s50 — if yes, "paper-faithful+patch" is a valid
recipe for scalar reproducibility.
**Parent**: R246 (parallel), R218 (paper-strict at s54 collapsed).

## TL;DR

Train td3_lstm scalar at s50 with --phi-h 1 --phi-d 1 --phi-f 100
--phi-abs 50 (paper-original weights + V4 patch). Outcomes:
- **RESCUE (geo ≥ 0.30)**: paper-faithful+patch works for scalar at
  non-s54 seeds. Cleanest paper recipe.
- **REGRESS (geo < 0.20)**: paper-original weights ALSO interfere
  for scalar at non-s54; only V4-rescaled weights work.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 1 --phi-d 1 --phi-f 100 --phi-abs 50 \
    --save-dir results/r248_w1_scalar_paperstrict_s50
```

## Cross-references

- R246 (scalar+only phi_abs at s50 = 0.2346)
- R218 (hreg paper-strict at s54 collapse)
- R72_w4 s50 baseline (~0.327 estimated)
