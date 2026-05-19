---
round: R211
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R211 plan — scalar at s51 + 50% comm-fail (complete 2x2 robustness grid)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, robustness grid completion)
**Driver**: R209 showed scalar at s54 degrades -12.2% under 50%
comm-fail (vs hreg's -3.4%). R211 tests same at s51 to verify the
"scalar 3.6× worse" claim is seed-universal.
**Parent**: R209/R210 verdicts.

## Target grid

| | perfect comm | 50% comm-fail |
|---|---|---|
| scalar s54 | 0.391 | 0.3431 (-12.2%) |
| **scalar s51** | 0.356 (R72_w4 s51) | **R211** |
| hreg s54 | 0.4152 | 0.4009 (-3.4%) |
| hreg s51 | 0.3901 | 0.3997 (+2.5%) |

After R211 the 2x2 grid completes the robustness comparison.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 51 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --comm-fail 0.50 \
    --save-dir results/r211_w1_scalar_commfail050_s51
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R209 (scalar s54 + 50% comm-fail = 0.3431)
- R210 (hreg s51 + 50% comm-fail = 0.3997)
- R181 (hreg s51 perfect comm = 0.3888)
- R72_w4 s51 baseline (scalar s51 perfect comm = 0.356)
