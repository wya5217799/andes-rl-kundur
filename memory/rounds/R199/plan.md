---
round: R199
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R199 plan — hreg λ=0.002 at s54, episodes=50 (test under-training axis)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, horizon axis test)
**Driver**: R191 (200ep) gave 0.3161 (over-training regression vs
R174's 75ep 0.4139). Untested: shorter horizon. Maybe 50ep gives
even higher than 75ep — the actor may overfit slightly between 50
and 75 episodes.
**Parent**: R174 (SOTA at 75ep), R191 (200ep regression).

## TL;DR

Train td3_lstm_hreg λ=0.002 at s54+offset=0, **50 episodes**. Three
outcomes:
- **NEW SOTA (geo > 0.4139)**: 75ep was slightly over-trained; 50ep
  is the optimal horizon. Queue R200 with 25ep or 60ep.
- **PARITY (0.40 ≤ geo ≤ 0.4139)**: 50ep is roughly equivalent to
  75ep; horizon is not load-bearing for hreg.
- **REGRESS (geo < 0.40)**: under-training; 75ep is necessary.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 50 --seed 54 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r199_w1_hreg_50ep_s54
```

ANDES WSL ~10 min train (shorter) + ~5 min eval.

## Cross-references

- R174 (75ep SOTA 0.4139)
- R191 (200ep regression 0.3161)
- R149 (200ep QR-LSTM regression — different algo, same direction)
