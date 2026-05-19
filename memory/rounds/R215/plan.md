---
round: R215
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R215 plan — phi_abs=10 (find minimum phi_abs threshold)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, reward-shaping threshold)
**Driver**: R214 phi_abs=0 = full collapse; R201 phi_abs=50 = SOTA.
Find the minimum phi_abs that prevents collapse. R215 = phi_abs=10
(R201's 1/5).
**Parent**: R214 verdict (phi_abs=0 collapse).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-abs 10.
Three outcomes:
- **STILL VIABLE (geo ≥ 0.39)**: phi_abs=10 is enough to escape
  collapse attractor; the term is breakout-kicker not load-bearing
  weight. **Paper claim**: minimum disclosure (just "a small
  Kundur-stability term").
- **PARTIAL (0.15 ≤ geo < 0.39)**: phi_abs=10 partly works; threshold
  is in [10, 50] range.
- **COLLAPSE (geo < 0.15)**: phi_abs=10 insufficient; threshold is
  higher than 10. R216 candidate = 25.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-abs 10 \
    --save-dir results/r215_w1_hreg_phiabs10_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R214 (phi_abs=0 collapse)
- R201 (phi_abs=50 SOTA)
- CLM-0203 (R103 paper_strict_pure)
