---
round: R217
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R217 plan — phi_abs=5 (narrow threshold bracket)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, threshold narrowing)
**Driver**: phi_abs threshold is in (2, 10]. R217=5 bisects.
**Parent**: R215 (10 near-SOTA), R216 (2 collapse).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-abs 5. If
viable (geo ≥ 0.30), threshold in (2, 5]; if collapse, in (5, 10].

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-abs 5 \
    --save-dir results/r217_w1_hreg_phiabs5_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R214/R216 (phi_abs=0/2 collapse)
- R215 (phi_abs=10 near-SOTA 0.4061)
- R201 (phi_abs=50 SOTA 0.4152)
