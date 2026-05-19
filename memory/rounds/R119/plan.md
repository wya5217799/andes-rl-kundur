---
round: R119
state: aborted
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: wider action bound replaced by R132 α-sweep (CLM-0218)
superseded_note: null
---
# R119 plan — Widen action bounds (DM/DD_MAX 2×) parallel to R115

**Status**: ACTIVE
**Opened**: 2026-05-19
**Driver**: PI "训练更好 agent". R93-W1 widen-bound experiment was held
pending PI direction; R100 falsified LSTM-drift as plateau cause but
left widen-bound untested. With ANDES WSL allowing 3 parallel python
processes (CLAUDE.md), launching this in parallel to R115 = no waste.
**Parent**: R92 / CLM-0170 (76% action saturation), CLM-0190 (R100
falsified drift mechanism; widen-bound is next mechanism candidate).

## TL;DR

Train with R72_w4 same hyper + seed 54 + 75 ep + `--dm-max 1200
--dd-max 1200` (2× paper default 600, action_penalty stays normalized
since DM_MAX/DD_MAX affect physical decoded action only, normalized
[-1,1] action range unchanged). Asks: if R72_w4 SOTA saturated 76% of
steps to ±1 (CLM-0170), does giving the policy 2× physical authority
let it use that headroom to lift geo, or does ENV dynamics constrain
the geo regardless?

If geo lifts above 0.42: widen-bound was load-bearing, env physical
action range is the ceiling.

If geo ≤ 0.39: bounds aren't the ceiling — confirms env/reward
structural ceiling per R100 mechanism story.

## Methodology

```
LR=1e-4 python scripts/train.py \
    --algo td3_lstm \
    --episodes 75 --seed 54 \
    --hidden-size 64 --tau 0.001 \
    --dm-max 1200 --dd-max 1200 \
    --normalize-actions \
    --lstm-lr-warmup-eps 5 \
    --save-dir results/r119_w1_widebound_s54
```

Asymmetric bounds (DM_MIN=-200 default, DD_MIN=-200 default) unchanged
— only widening UP. ~15 min ANDES wave.

## Gate criteria

- **CONFIRM (geo ≥ 0.42)**: action bound is the ceiling; paper writeup
  defends paper-spec 600 limit choice OR proposes 1200 as engineering
  improvement.
- **MARGINAL (geo ∈ [0.36, 0.42])**: bounds give some headroom but
  not the full story. Env/reward still structural.
- **REGRESS (geo < 0.36)**: wider bounds destabilise; agent over-acts.
  R72_w4's bound choice is well-tuned.
- **EQUAL (~0.39)**: action bounds NOT load-bearing; final
  confirmation of R100 env-ceiling story.

## Cross-references

- CLM-0170 (76% saturation R92-W1)
- CLM-0190 (R100 drift falsified)
- CLM-0144 (91-round plateau)
- R93 plan (widen-bound was original PRIORITY 1 before LSTM-drift
  story emerged)
