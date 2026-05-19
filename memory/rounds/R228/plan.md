---
round: R228
state: completed
opened: '2026-05-19'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R228 plan — SOTA hyper at --dm-max 600 (2× action bound, R119 question revisited)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, action-bound axis)
**Driver**: R119 was aborted (CLM-0218 took different path). dm_max
widening never tested at SOTA hyper. Tests whether the 75ep horizon
peak shifts up if actor has more action range.
**Parent**: R201 (SOTA at default dm_max=300), R119 (aborted predecessor).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --dm-max 600 --dd-max 600
(2× default action bound). Three outcomes:
- **NEW SOTA (geo > 0.4152)**: wider bound lets policy take
  more decisive actions; queue further widening.
- **PARITY**: bound is not load-bearing at SOTA.
- **REGRESS**: wider bound destabilizes; tight bound is intentional.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --dm-max 600 --dd-max 600 \
    --save-dir results/r228_w1_hreg_dmmax600_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (default dm_max SOTA)
- R119 (aborted predecessor)
- CLM-0218 (R132 α-sweep took different path)
