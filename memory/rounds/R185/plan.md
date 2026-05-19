---
round: R185
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R185 plan — hreg λ=0.002 at s50 (original Q-0005 seed)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, complete Q-0005 seed picture)
**Driver**: R183 confirmed hreg λ=0.002 does NOT rescue s49 collapse
(CLM-0345). Q-0005 was originally opened about s50 (the seed that
collapsed at R56). Testing R174 SOTA hyper at s50 completes the 4-seed
picture {49, 50, 51, 54} and pins down the collapse-vs-viable seed
distribution.

## TL;DR

Train td3_lstm_hreg λ=0.002 at s50, 75ep. Three outcomes:
- **VIABLE (geo ≥ 0.35)**: s50 works under hreg → s49 is the only
  surviving collapse seed in tested set; 3/4 viable.
- **PARTIAL (0.10 ≤ geo < 0.35)**: hreg lifts s50 partially but
  doesn't reach baseline → both s50 and s49 are mechanism-collapse
  seeds.
- **COLLAPSE (geo < 0.10)**: hreg doesn't rescue s50 either → 2/4
  seeds collapse; "lucky seed" caveat in paper is strong.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r185_w1_hreg_lambda0p002_s50
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- CLM-0345 (R183 s49 collapse confirmed)
- CLM-0295 (R72_w4 s49 collapse, R72_w4 s51 -8.9%)
- Q-0005 (R56, "Why does TD3+LSTM seed 50 collapse")
- R174 (single-policy SOTA at s54 with same hyper)
