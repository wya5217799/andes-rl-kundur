---
round: R204
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R204 plan — R201 hyper (tau=0.005) at s50 (complete cross-seed universality picture)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, R201 cross-seed s50)
**Driver**: R201 (+0.3% at s54) and R203 (+0.3% at s51) both show
identical lift from tau=0.001 → tau=0.005. R204 tests s50 to
complete the cross-seed universality picture (3 viable seeds).
**Parent**: R201 verdict, R203 verdict.

## TL;DR

Train td3_lstm_hreg λ=0.002 at s50+offset=0 with tau=0.005, 75ep.
Expected (based on +0.3% pattern): geo ~0.353 (vs R185 s50,
tau=0.001 = 0.3515).

Three outcomes:
- **+0.3% LIFT (geo ≈ 0.353)**: pattern holds across 3 seeds; SOTA
  hyper universality firmly established. Paper claim: "tau=0.005
  is strictly better than tau=0.001 by ~0.3% across viable seeds."
- **NO LIFT (geo ≈ 0.35)**: tau lift inconsistent; need 4th seed.
- **REGRESS (geo < 0.34)**: tau=0.005 hurts s50; lift is s51/s54-specific.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r204_w1_hreg_tau005_s50
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R185 (s50 baseline at tau=0.001 = 0.3515)
- R203 (s51 lift confirmed)
- R201 (s54 lift)
