---
round: R196
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R196 plan — scalar td3_lstm at s54+offset=50 (complete the 2x2 algo×offset grid)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop; complete robustness comparison grid)
**Driver**: R193 + R194 established hreg cross-offset mean ≈0.397
across {0, 50, 100}. R192 has scalar at offset=100 (0.2844, -27%
drop). Missing: scalar at offset=50. R196 fills the grid for a clean
hreg-vs-scalar offset-robustness comparison.

## Target grid

| | offset=0 | offset=50 | offset=100 |
|---|---|---|---|
| scalar | 0.391 (R72_w4) | **R196** | 0.2844 (R192) |
| hreg | 0.4139 (R174) | 0.3882 (R194) | 0.3875 (R193) |

After R196 the grid is complete and the paper claim "hreg has lower
offset-variance than scalar" gets its third data point.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --seed-offset 50 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --save-dir results/r196_w1_scalar_s54_offset50
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R72_w4 / CLM-0123 (scalar s54 offset=0 baseline 0.391)
- R192 verdict (scalar s54 offset=100 = 0.2844)
- R174 (hreg s54 offset=0 SOTA 0.4139)
- R193 verdict (hreg s54 offset=100 = 0.3875)
- R194 verdict (hreg s54 offset=50 = 0.3882)
