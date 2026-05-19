---
round: R178
state: superseded
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: R173
abort_reason: null
superseded_note: Bit-identical duplicate of R173 (parallel session ran λ=0.001 at
  s54 first). Numbers match to 8 decimals; reproducibility confirmed. No new info.
type: research
---
# R178 plan — hreg λ=0.001 at s54 (extend R170→R174 dose-response down)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, hreg λ refinement)
**Driver**: R170 (λ=0.003) geo 0.4091 → R174 (λ=0.002) geo 0.4139.
Dose-response is climbing at smaller λ. R178 tests λ=0.001 to find
the peak or confirm R174 sits at it. User said "继续 别提醒我" =
autonomous mode.
**Parent**: CLM-0325 (R170 dose-response), R174 verdict (current SOTA).

## TL;DR

Train `td3_lstm_hreg` at s54 with λ_h=0.001. Three outcomes:
- **BREAK >R174 0.4139**: new SOTA, λ scan continues; R179 → λ=0.0005
- **Plateau ≈ R174 0.4139**: sweet spot bracket [0.001, 0.002];
  R179 → fine sweep {0.0015, 0.0025}
- **REGRESS < R170 0.4091**: λ=0.001 too small (under-regularised
  back toward R72_w4 baseline); stop dose-response, pivot

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.001 \
    --save-dir results/r178_w1_hreg_lambda0p001_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Gate

- **NEW SOTA (geo > 0.4139)**: close-positive; queue R179 λ=0.0005
- **CONFIRMED PLATEAU (geo ∈ [0.41, 0.4139])**: close-positive; R179
  fine-sweep
- **MARGINAL (geo ∈ [0.39, 0.41))**: close-partial; not a lifter
- **REGRESS (geo < 0.39)**: close-negative; λ=0.001 under-regs

## Cross-references

- R174 verdict (current single-policy SOTA 0.4139)
- CLM-0325 (R171 dose-response narrative — R178 adds 4th datapoint)
- CLM-0190 (R100 original hreg work)
