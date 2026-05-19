---
round: R183
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R183 plan — hreg λ=0.002 at s49 (test Q-0005 mechanism: does hreg rescue collapse?)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, hreg seed robustness + Q-0005 mechanism)
**Driver**: After R178 turned out to be a duplicate of R173, the
remaining high-value untested axis is **R174 SOTA hyper at s49**.
R72_w4 hyper at s49 collapsed completely (geo=0.0100, CLM-0295).
R181 already showed R174 hyper at s51 = 0.3888 (-2.5% vs s54).
The s49 test is the toughest robustness check — if hreg λ=0.002
also rescues s49 (geo ≥ 0.3), it's a strong mechanism finding for
Q-0005 (the seed collapse question opened R56).
**Parent**: R174 (SOTA), R181 (s51 seed test), CLM-0295 (s49 collapse).

## TL;DR

Train `td3_lstm_hreg` λ_h=0.002 at s49 75ep. Three outcomes:
- **STRONG (geo ≥ 0.39)**: hreg fully rescues the s49 collapse →
  Q-0005 closed-positive by hreg regularisation
- **PARTIAL (geo ∈ [0.20, 0.39))**: hreg partially mitigates collapse
  → Q-0005 closed-partial; mechanism = hreg dampens but doesn't kill
  seed-dependent attractor
- **COLLAPSE (geo < 0.20)**: hreg does NOT rescue s49 → Q-0005
  closed-negative for hreg; mechanism is deeper (independent of
  actor-state regularisation)

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 49 --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r183_w1_hreg_lambda0p002_s49
```

ANDES WSL ~15 min train + ~5 min eval.

## Gate

See TL;DR. Result will either close Q-0005 (positive / partial /
negative) or yield a follow-up axis.

## Cross-references

- R174 (single-policy SOTA at s54, λ=0.002 → 0.4139)
- R181 (multi-seed s51, λ=0.002 → 0.3888)
- CLM-0295 (R72_w4 s49 collapse evidence)
- Q-0005 (R56, "Why does TD3+LSTM seed 50 collapse")
