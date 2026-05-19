---
round: R222
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R222 plan — SOTA hyper at --vsg-m0 100 (H₀=50, half default inertia)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, physical-parameter robustness)
**Driver**: Default V4 paper-faithful has vsg_m0=200 (H₀=100s).
Halving to vsg_m0=100 (H₀=50s) tests SOTA generalization to a
different physical inertia. Paper-relevant — paper Sec.IV-C runs
multiple inertia configs. Robust SOTA across physical params is a
strong publication claim.
**Parent**: R201 (SOTA at vsg_m0=200).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --vsg-m0 100. Three
outcomes:
- **ROBUST (geo ≥ 0.35)**: SOTA generalizes to lower-inertia regime;
  paper claim "physical robustness".
- **PARTIAL (0.20 ≤ geo < 0.35)**: SOTA depends partly on inertia
  value; characterize curve.
- **COLLAPSE (geo < 0.10)**: SOTA is inertia-specific; train-time
  inertia is a critical assumption.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-m0 100 \
    --save-dir results/r222_w1_hreg_m0_100_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at vsg_m0=200)
- v4_config.py vsg_m0 docstring
- R160 (disturbance magnitude robustness ±20%)
