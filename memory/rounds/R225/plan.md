---
round: R225
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R225 plan — SOTA hyper at --vsg-m0 300 (1.5× inertia, fill high-side curve)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, asymmetric robustness characterization)
**Driver**: R224 (2× = -34%) revealed asymmetric robustness. R225
fills the gap at 1.5× to characterize whether breakdown is sudden
(threshold near 1.5×) or gradual (linear -17% expected).
**Parent**: R201 (1× SOTA), R224 (2× fragile).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --vsg-m0 300. Three outcomes:
- **LINEAR (geo ≈ 0.34)**: gradual degradation; breakdown is linear
  in inertia ratio above 1×.
- **SUDDEN (geo < 0.30)**: breakdown is sharp between 1× and 1.5×;
  characterize threshold further with R226 = 1.25×.
- **MILD (geo > 0.38)**: gentle degradation up to 1.5×; sharp drop
  from 1.5× to 2×.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-m0 300 \
    --save-dir results/r225_w1_hreg_m0_300_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201/R222/R223/R224 (inertia curve)
