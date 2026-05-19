---
round: R223
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R223 plan — SOTA hyper at --vsg-m0 50 (H₀=25, quarter inertia)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, physical-param extreme)
**Driver**: R222 (half inertia) -3.0% only. Extreme test at quarter
inertia (H₀=25s). If still ≥0.35, "robust to 4× inertia variation"
becomes a powerful publication claim.
**Parent**: R222 verdict.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --vsg-m0 50. Three outcomes:
- **STRONG ROBUST (geo ≥ 0.35)**: 4× inertia variation, banger claim.
- **PARTIAL (0.20 ≤ geo < 0.35)**: graceful degradation; characterize
  the breakdown curve.
- **COLLAPSE (geo < 0.10)**: inertia threshold reached; paper reports
  "robust up to 2× variation".

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-m0 50 \
    --save-dir results/r223_w1_hreg_m0_50_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (vsg_m0=200 SOTA 0.4152)
- R222 (vsg_m0=100 = 0.4028, -3.0%)
