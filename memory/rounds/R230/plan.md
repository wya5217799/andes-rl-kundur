---
round: R230
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R230 plan — scalar (no hreg) at gamma=0.95 (test hreg-specificity of gamma-insensitivity)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, hreg vs scalar comparison)
**Driver**: R229 showed gamma=0.95 only -0.5% drop for hreg SOTA.
R230 tests scalar at same gamma — does scalar also tolerate gamma
deviations? If scalar drops more, hreg-stability extends to gamma
robustness too.
**Parent**: R229 verdict, R209 (scalar control at comm-fail).

## TL;DR

Train td3_lstm (scalar) at s54 with tau=0.005 + gamma=0.95. Compare to:
- R72_w4 baseline (scalar, gamma=0.99): 0.391
- R229 (hreg, gamma=0.95): 0.4133

Three outcomes:
- **SCALAR ROBUST (geo ≥ 0.38)**: gamma is not load-bearing for either
  algo; not a hreg-specific feature.
- **SCALAR PARTIAL (0.30 ≤ geo < 0.38)**: scalar more gamma-sensitive
  than hreg; hreg-stability extends to gamma.
- **SCALAR COLLAPSE (geo < 0.30)**: gamma=0.95 breaks scalar; hreg's
  stability is the rescue.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --gamma 0.95 \
    --save-dir results/r230_w1_scalar_gamma095_s54
```

## Cross-references

- R229 (hreg gamma=0.95 = 0.4133)
- R72_w4 (scalar default gamma=0.99 = 0.391)
- R209 (scalar control at comm-fail=50%)
