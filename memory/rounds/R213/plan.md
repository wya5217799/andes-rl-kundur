---
round: R213
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R213 plan — hreg SOTA hyper at gamma=0.999 (long-horizon discount)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, gamma axis)
**Driver**: Default gamma=0.99 is the project standard. Higher gamma
(0.999) makes the agent care more about long-term reward, which might
help LS2 (steady-state settling, long-horizon) at slight LS1 cost.
**Parent**: R201 (SOTA at gamma=0.99 default).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --gamma 0.999 for
75ep. Three outcomes:
- **HIGHER (geo > 0.4152)**: long-horizon discount improves SOTA;
  search continues with 0.995 / 0.9995.
- **EQUIVALENT (0.40 ≤ geo ≤ 0.4152)**: gamma is robust between
  0.99 and 0.999.
- **REGRESS (geo < 0.40)**: 0.999 is too long-sighted; LS1 hurt.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --gamma 0.999 \
    --save-dir results/r213_w1_hreg_gamma0p999_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at default gamma)
- R191 (200ep regress, gamma=0.99)
- CLM-0094 (R72_w4 hyper definition)
