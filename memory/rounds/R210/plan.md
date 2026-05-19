---
round: R210
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R210 plan — hreg at s51 + 50% comm-fail (cross-seed verification of comm-fail robustness)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, cross-seed comm-fail)
**Driver**: R208 confirmed hreg at s54 retains 96.6% perf under 50%
comm-fail. R210 verifies cross-seed: if s51 also retains ≥0.36 (i.e.
≥hreg s51 baseline R203's 0.3901 × 0.92 = 0.359), comm-fail robustness
is seed-universal. Crucial for "deployment-ready" paper claim.
**Parent**: R208 (s54 comm-fail 0.4009), R203 (s51 baseline 0.3901).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s51 with --comm-fail 0.50.
Outcomes:
- **CROSS-SEED ROBUST (geo ≥ 0.36, i.e. -8% or less)**: comm-fail
  robustness is seed-universal. Paper headline strengthens.
- **PARTIAL (0.30 ≤ geo < 0.36)**: s51 less robust than s54 to
  comm-fail; still publishable.
- **REGRESS (geo < 0.30)**: cross-seed degradation; robustness is
  s54-specific (combined with other lucky-s54 factors).

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 51 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --comm-fail 0.50 \
    --save-dir results/r210_w1_hreg_commfail050_s51
```

## Cross-references

- R208 (s54 comm-fail 50% = 0.4009)
- R203 (s51 perfect comm at tau=0.005 = 0.3901)
- R209 (scalar control = 0.3431)
- R206/R207 (s54 robustness curve)
