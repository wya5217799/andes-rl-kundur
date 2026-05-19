---
round: R203
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R203 plan — R201 hyper (tau=0.005) at s51 (cross-seed transfer test)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, R201 cross-seed)
**Driver**: R201 (tau=0.005) new SOTA at s54. Test transferability:
does the +0.3% lift over tau=0.001 also appear at s51? R181 (s51,
tau=0.001) = 0.3888. If R203 (s51, tau=0.005) > 0.3888, the new
hyper is seed-universal.
**Parent**: R201 verdict (new SOTA), R181 (s51 baseline).

## TL;DR

Train td3_lstm_hreg λ=0.002 at s51+offset=0 with tau=0.005 for 75ep.
Three outcomes:
- **LIFT (geo > 0.3888)**: new SOTA hyper is seed-universal; queue
  R204 at s50 to fully validate.
- **PARITY (geo ≈ 0.3888)**: tau lift is s54-specific.
- **REGRESS (geo < 0.3888)**: tau=0.005 worse at s51 than tau=0.001;
  R181's tau=0.001 may have been incidentally optimal for s51.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 51 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r203_w1_hreg_tau005_s51
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (new SOTA at s54 with tau=0.005)
- R181 (s51 baseline at tau=0.001 = 0.3888)
- R174 (prev SOTA at s54 with tau=0.001 = 0.4139)
