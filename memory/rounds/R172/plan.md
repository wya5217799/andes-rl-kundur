---
round: R172
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R172 plan — Q-0020 transient-phase replay reweighting (×3 on step 0-5)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (Q-0020 closure attempt)
**Driver**: User said 启动训练 after R171 ledger fixes. Q-0020 is the
last untested algorithm-side single-policy axis (hypothesis: oversample
transient-phase samples to break 0.391 plateau on R72_w4 hyper).
**Parent**: Q-0020 (R88), CLM-0123 (R72_w4 SOTA baseline 0.391).

## TL;DR

Train td3_lstm at R72_w4 hyper (lr=1e-4 clamp, tau=0.001, warmup=5) on
s54, but with `--transient-boost=3.0 --transient-window=6` so that
subsequence start indices in [0,6) are 3× weighted relative to the
~36 remaining valid starts in each episode. This implements Q-0020's
hypothesis directly: weighting step-0..5 (disturbance recovery phase)
breaks the plateau by improving early-transient credit assignment.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --transient-boost 3.0 --transient-window 6 \
    --save-dir results/r172_w1_td3_lstm_tb3_s54
```

Hyper otherwise IDENTICAL to R72_w4 SOTA so any geo delta is
attributable to the reweighting alone.

ANDES WSL ~15 min. Eval ~10 min.

## Gate

- **BREAK (geo ≥ 0.42)**: Q-0020 closed-positive; new project SOTA
  candidate; paper Sec.IV-D adds transient-reweight section
- **CONTRIBUTOR (geo ∈ [0.35, 0.42))**: closed-partial; ensemble
  candidate (test R172 in 5-way combo)
- **NEUTRAL [0.30, 0.35)**: closed-negative for plateau-break; weak
  ensemble candidate
- **WEAK/COLLAPSE (< 0.30)**: closed-negative; 92nd single-algo neg
  datapoint

## Cross-references

- Q-0020 (R88 opening: "Does transient-phase replay reweighting...")
- CLM-0123 (R72_w4 SOTA reference)
- CLM-0295 (R154 ensemble SOTA 0.4119)
- CLM-0325 (R170 single-policy near-SOTA 0.4091 — R172 needs to beat this)
- CLM-0330 (R171 Gap fixes infra anchor)
