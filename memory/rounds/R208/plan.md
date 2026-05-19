---
round: R208
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R208 plan — SOTA hyper at comm-fail=0.50 (extreme — find breakdown threshold)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, robustness extreme)
**Driver**: R207 (20% comm-fail) only -3.9% degradation. Push to 50%
to either confirm "robust even at extreme packet loss" or find the
breakdown threshold of the SOTA hyper.
**Parent**: R206/R207 verdicts (robustness curve).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --comm-fail 0.50
(50% inter-agent packet drop). Three outcomes:
- **STILL ROBUST (geo ≥ 0.30)**: half the messages can drop without
  catastrophic failure. Strongest possible paper claim.
- **DEGRADES BUT VIABLE (0.20 ≤ geo < 0.30)**: graceful breakdown,
  characterize curve.
- **COLLAPSE (geo < 0.20)**: 50% is the breakdown threshold; paper
  reports "robust up to ~30-40% packet drop".

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --comm-fail 0.50 \
    --save-dir results/r208_w1_hreg_commfail050_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (perfect comm SOTA 0.4152)
- R206 (5% comm-fail = 0.4144)
- R207 (20% comm-fail = 0.3990)
