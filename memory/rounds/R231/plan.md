---
round: R231
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R231 plan — SOTA hyper at phi_h=0.05 (10× V4 default, untested mid-range)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, reward landscape mid-range)
**Driver**: phi_h mapped at endpoints — V4 0.0056 (R201 SOTA), paper-
original 1 (R218 collapse with phi_abs=0). Untested mid-range
phi_h=0.05 (~10× V4). Could be a different reward basin.
**Parent**: R201 (SOTA), R218 (paper-strict collapse).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --phi-h 0.05 --phi-d 0.05
(symmetric scaling). Three outcomes:
- **NEW BASIN (geo > 0.40 with different LS1/LS2 ratio)**: phi_h=0.05
  finds a different policy archetype; characterize tradeoff.
- **PARITY**: phi_h is flat in [0.006, 0.05] range.
- **COLLAPSE (geo < 0.10)**: phi_h=0.05 disrupts the reward
  landscape; threshold is between 0.006 and 0.05.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-h 0.05 --phi-d 0.05 \
    --save-dir results/r231_w1_hreg_phih005_s54
```

## Cross-references

- R201 (V4 default phi_h=0.0056 SOTA)
- R218 (paper-strict phi_h=1 collapse without phi_abs)
- R219 (paper-strict + phi_abs=50 also collapse)
