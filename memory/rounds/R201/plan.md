---
round: R201
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R201 plan — hreg λ=0.002 at s54 with tau=0.005 (default target update speed)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, tau axis)
**Driver**: R174 SOTA uses tau=0.001 (5× slower than default 0.005).
Untested: does the slow target update matter, or would default 0.005
give same/better result? Faster target updates might help LS1
convergence within budget.
**Parent**: R174 (SOTA at tau=0.001).

## TL;DR

Train td3_lstm_hreg λ=0.002 at s54+offset=0 with tau=0.005, 75ep.
Three outcomes:
- **NEW SOTA (geo > 0.4139)**: default tau already optimal; R174's
  slow tau is unnecessary or even slightly suboptimal.
- **PARITY (0.40 ≤ geo ≤ 0.4139)**: tau is robust; either works.
- **REGRESS (geo < 0.40)**: tau=0.001 is necessary for hreg stability.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r201_w1_hreg_tau005_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R174 (SOTA at tau=0.001)
- R199 (50ep collapse)
- R200 (lr=5e-5 collapse)
- CLM-0094 (R72_w4 hyper)
