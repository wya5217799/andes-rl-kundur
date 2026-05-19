---
round: R123
state: superseded
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: R127
abort_reason: null
superseded_note: AFE critic absorbed into stacked path R127 (CLM-0234)
---
# R123 plan — AFE critic (TD3-AFE-LSTM) first training, queued

**Status**: QUEUED (fires as soon as one of R115/R119/R122 frees a WSL slot)
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent". CLM-0157(b) PRIORITY 2 R98 built
`TD3AfeLstmAgent` (critic input augmented to `[obs, a, a², |a|, sign(a)]`);
R108 wired into train.py. No session trained it yet.
**Parent**: CLM-0157(b) candidate, R83 unlock.

## TL;DR

Train `td3_afe_lstm` with R72_w4 same hyper + seed 54 + 75 ep. Tests
"action feature engineering" mechanism candidate — does giving the
critic explicit nonlinear action features change the bang-bang attractor?

## Command (queued)

```
LR=1e-4 python scripts/train.py \
    --algo td3_afe_lstm \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r123_w1_afe_s54
```

## Gate

- CONFIRM (geo ≥ 0.42): AFE lifts geo; action features were missing.
- MARGINAL [0.36, 0.42]: AFE helps modestly.
- REGRESS / EQUAL (< 0.36 or ~0.39): AFE doesn't help; final
  confirmation env/reward is the ceiling.

## Cross-references

- CLM-0157(b), R98/R108 verdicts
- CLM-0190 (R100 drift falsified)
- CLM-0144 (91-round plateau)
