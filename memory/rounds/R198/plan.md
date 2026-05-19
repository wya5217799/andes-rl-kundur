---
round: R198
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R198 plan — hreg λ=0.002 at NEW seed s55 (search for luckier seed than s54)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, seed search)
**Driver**: Tested seeds so far {49 collapse, 50 0.35, 51 0.39, 54 SOTA
0.4139}. s54 is "lucky" but could there be an even luckier untested
seed? R198 tries s55 — adjacent to s54, may share basin or differ.
**Parent**: CLM-0350 (Q-0005 closed-partial), R174 verdict (SOTA).

## TL;DR

Train td3_lstm_hreg λ=0.002 at s55 offset=0 75ep. Outcomes:
- **NEW SOTA (geo > 0.4139)**: s55 luckier than s54; new headline
  number; potential further seed search at s52/s53/s56.
- **VIABLE (0.30 ≤ geo ≤ 0.4139)**: s55 is another viable seed; adds
  to multi-seed mean; no SOTA change.
- **COLLAPSE (geo < 0.10)**: s55 is another bad seed like s49;
  collapse rate updates.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 55 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r198_w1_hreg_s55
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R174 (s54 SOTA 0.4139)
- R181 (s51 viable -2.5%)
- R185 (s50 rescued 0.3515)
- R183 (s49 collapse)
- CLM-0350 (Q-0005 mechanism)
