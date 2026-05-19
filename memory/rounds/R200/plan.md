---
round: R200
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R200 plan — hreg λ=0.002 at s54 with lr=5e-5 (lower learning rate test)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, lr axis)
**Driver**: R174 SOTA uses lr=1e-4 (clamped). Lower lr (5e-5) might
converge to a tighter optimum within 75ep without changing horizon.
Could find new SOTA if R174 is slightly over-stepping the optimum.
**Parent**: R174 verdict (SOTA at default lr), R199 verdict (horizon
basin map).

## TL;DR

Train td3_lstm_hreg λ=0.002 at s54+offset=0 with **lr=5e-5** for 75ep.
Three outcomes:
- **NEW SOTA (geo > 0.4139)**: lower lr finds tighter optimum; new
  hyperparameter found.
- **PARITY (0.40 ≤ geo ≤ 0.4139)**: lr=1e-4 already optimal; lr is
  not load-bearing.
- **REGRESS (geo < 0.40)**: too low lr; under-converges in 75ep.

## Methodology

```
LR=5e-5 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r200_w1_hreg_lr5e5_s54
```

Note: LR env var passed as 5e-5; train.py respects LSTM_LR_UNCLAMP
behavior — actual lr will be min(LR, 1e-4) by default which gives
5e-5 (under clamp).

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R174 (SOTA at lr=1e-4)
- R199 (50ep collapse — horizon dependency)
- CLM-0094 (R72_w4 hyper definition)
