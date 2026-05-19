---
round: R239
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R239 plan — scalar (no hreg) + only phi_abs (paper-Eq.14-inertness algo-universal?)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, paper-integrity algorithm test)
**Driver**: R238 (hreg + only phi_abs) gave 0.4128 — paper Eq.14
inert with hreg. R239 tests if scalar (no hreg) ALSO works with only
phi_abs. If yes, the paper-Eq.14-inertness is universal across algos;
if scalar collapses, the finding is hreg-specific.
**Parent**: R238, R72_w4 (scalar baseline with full reward).

## TL;DR

Train td3_lstm scalar at s54 with --phi-h 0 --phi-d 0 --phi-f 0
(only phi_abs=50 active). Three outcomes:
- **SCALAR SOTA (geo ≥ 0.38)**: paper-Eq.14-inertness is universal
  (algo-independent property of V4 reward landscape). Most decisive
  paper claim possible.
- **PARTIAL (0.25 ≤ geo < 0.38)**: scalar uses paper terms partly;
  hreg's robustness makes paper-Eq.14 irrelevant only for hreg.
- **COLLAPSE (geo < 0.10)**: paper Eq.14 terms ARE necessary for
  scalar; only hreg can train without them.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r239_w1_scalar_onlyphiabs_s54
```

## Cross-references

- R238 (hreg + only phi_abs = 0.4128)
- R72_w4 (scalar full reward = 0.391)
- R209 (scalar comm-fail control)
