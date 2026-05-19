---
round: R244
state: completed
opened: '2026-05-20'
closed: '2026-05-20'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R244 plan — SAC algorithm (untested in autonomous loop, entropy-regularized)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, untested algorithm class)
**Driver**: SAC has entropy-regularized exploration which is
fundamentally different from TD3 family. Untested in autonomous loop.
Could produce different policy archetype or new SOTA.
**Parent**: R201 (TD3 hreg SOTA).

## TL;DR

Train SAC algorithm at s54 with default hyper for 75ep. Compare to:
- R72_w4 baseline TD3 scalar at s54: 0.391
- R201 td3_lstm_hreg SOTA: 0.4152
- Old CLM-0101 SAC h64 combo paper-faithful: -0.194 (paper-metric)

## Methodology

```
python scripts/train.py --algo sac \
    --episodes 75 --seed 54 --hidden-size 64 \
    --normalize-actions \
    --save-dir results/r244_w1_sac_s54
```

## Cross-references

- R201 (TD3 hreg SOTA at default hyper)
- CLM-0101 (older SAC results pre-LSTM era)
