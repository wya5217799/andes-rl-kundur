---
round: R238
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R238 plan — ONLY phi_abs (disable all paper Eq.14 terms)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, decisive paper-integrity test)
**Driver**: R236 + R237 individually disabled each Eq.14 term with
near-SOTA results. R238 disables ALL Eq.14 terms simultaneously
(phi_h=phi_d=phi_f=0) with only phi_abs=50 active. Three outcomes:
- **SOTA (geo ≥ 0.40)**: phi_abs is *sufficient*; paper Eq.14 is
  entirely vestigial. Decisive paper-integrity finding.
- **PARTIAL (0.30 ≤ geo < 0.40)**: terms have small additive
  contributions that disappear individually but matter combined.
- **COLLAPSE (geo < 0.20)**: terms interact; can't ablate all at
  once even though each individually inert.

**Parent**: R236/R237 verdicts.

## TL;DR

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r238_w1_hreg_onlyphiabs_s54
```

## Cross-references

- R236 (phi_h/phi_d=0)
- R237 (phi_f=0)
- R214 (phi_abs=0 collapse)
- R218 (paper-strict collapse)
