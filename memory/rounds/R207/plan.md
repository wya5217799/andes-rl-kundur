---
round: R207
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R207 plan — SOTA hyper at comm-fail=0.20 (severe comm-failure stress test)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, robustness curve)
**Driver**: R206 showed -0.2% only at 5% comm-fail. Jump to 20%
directly (skipping 10%) to test the extreme — if SOTA hyper holds
above 0.35 at 20% packet drop, paper claim becomes very strong.
**Parent**: R206 verdict.

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --comm-fail 0.20.
Three outcomes:
- **STRONG ROBUST (geo ≥ 0.39)**: <6% degradation at 20% packet drop.
  Exceptional finding; paper headline.
- **PARTIAL ROBUST (0.30 ≤ geo < 0.39)**: graceful degradation;
  publishable robustness claim.
- **FRAGILE (geo < 0.30)**: SOTA breaks down at high comm-fail; paper
  must disclose breakdown threshold.

If R207 holds well, R208 = 0.10 fills in the curve. If R207 fragile,
R208 = 0.10 finds the threshold.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --comm-fail 0.20 \
    --save-dir results/r207_w1_hreg_commfail020_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at comm_fail=0 = 0.4152)
- R206 (5% comm-fail = 0.4144)
