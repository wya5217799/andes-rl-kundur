---
round: R216
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R216 plan — phi_abs=2 (find true minimum breakout threshold)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, threshold refinement)
**Driver**: phi_abs sweep: 0 collapse, 10 near-SOTA, 50 SOTA. R216
tests 2 to find the true minimum. If 2 works, the threshold is
near-zero (any non-trivial term breaks collapse). If 2 collapses,
threshold is in (2, 10].
**Parent**: R214 (0 collapse), R215 (10 near-SOTA).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-abs 2.
Three outcomes:
- **VIABLE (geo ≥ 0.30)**: threshold is near-zero; phi_abs is a
  tiny breakout kicker. Paper claim: "any small additive penalty
  breaks the collapse attractor".
- **PARTIAL (0.05 ≤ geo < 0.30)**: threshold is in (0, 2-10] range.
- **COLLAPSE (geo < 0.05)**: threshold is in (2, 10]; R217 = 5.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-abs 2 \
    --save-dir results/r216_w1_hreg_phiabs2_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R214 (phi_abs=0 collapse)
- R215 (phi_abs=10 near-SOTA)
- R201 (phi_abs=50 SOTA)
