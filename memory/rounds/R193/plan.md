---
round: R193
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R193 plan — hreg λ=0.002 at s54+offset=100 (test offset-robustness of hreg)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop)
**Driver**: R192 showed scalar s54+offset=100 drops to 0.2844 (-27%
vs baseline 0.391). Does hreg λ=0.002 *stabilize* across offsets, or
does it also drop? If hreg stays near 0.40+, it's a strong paper
claim about RNG-path robustness. If it drops too, offset-dependency
is universal.

## TL;DR

Train `td3_lstm_hreg` λ=0.002 at s54+seed-offset=100, 75ep. Three
outcomes:
- **HREG-ROBUST (geo ≥ 0.39)**: hreg matches R72_w4 baseline at
  offset=0 even with offset=100; **publication finding** —
  hreg recommended for RNG-path stability.
- **PARTIAL (0.32 ≤ geo < 0.39)**: hreg buffers but doesn't fully
  stabilize; intermediate finding.
- **OFFSET-DEPENDENT (geo < 0.32, similar to R192's 0.2844)**:
  offset-dependency is universal, hreg adds nothing to robustness.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --seed-offset 100 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r193_w1_hreg_s54_offset100
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R174 (hreg s54 offset=0 = SOTA 0.4139)
- R192 (scalar s54 offset=100 = 0.2844)
- R72_w4 (scalar s54 offset=0 = 0.391)
- R188/R190 (env-side mechanism at s49)
