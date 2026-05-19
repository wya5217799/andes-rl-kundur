---
round: R156
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R156 plan — td3 MLP (non-recurrent) at s54 for ensemble diversity

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: R154 SOTA (CLM-0295) = geo 0.4119 via 4-way cross-algo at
same seed s54. Next step: find more structurally distinct policy families
to add 5+-way ensemble that may break 0.42 BREAK threshold.
**Parent**: CLM-0295 (R154 PROJECT SOTA), CLM-0144 (91-round plateau).

## TL;DR

Train td3 MLP (non-LSTM, non-recurrent) at s54 baseline hyper. All 4
current ensemble members (R72_w4, R142, R143, R100) are LSTM-based;
adding a non-recurrent MLP policy adds the most structurally distinct
algorithmic family available. If MLP geo ≥ 0.35 (better than R150's
0.350 which we know hurts), it may contribute to ensemble lift.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3 \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --save-dir results/r156_w1_td3_mlp_s54
```

No --lstm-lr-warmup-eps (TD3 MLP doesn't have LSTM-specific warmup).
Lr at 1e-4 (matches R72_w4 hyper clamp). ANDES WSL ~15 min.

## Gate

- **CONTRIBUTOR (geo ≥ 0.35)**: add to ensemble; if 5-way > 0.4119,
  promoted to project SOTA.
- **NEUTRAL [0.30, 0.35]**: marginal; test in ensemble anyway.
- **WEAK (< 0.30)**: skip from ensemble (R150-style drag).

## Cross-references

- CLM-0295 (R154 PROJECT SOTA, 4-way cross-algo)
- CLM-0094 (R72_w4 LSTM baseline at s54)
- Q-0014 (algo backlog, now obsolete per R154)
