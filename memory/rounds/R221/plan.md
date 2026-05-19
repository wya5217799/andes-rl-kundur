---
round: R221
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R221 plan — SOTA hyper + --phi-max 1.0 (enable R31 max-disturbance shaping)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, untested reward shaping axis)
**Driver**: R31 shaping (`r_max_df = -max_i(|d_omega|)^2`) is OFF by
default (phi_max=0). Enabling it adds a worst-agent penalty that may
shift the actor toward more equitable disturbance recovery across
agents. Could improve LS1 (where worst-agent damping matters).
**Parent**: R201 (SOTA at phi_max=0).

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-max 1.0
(enable the previously-disabled R31 worst-agent max-disturbance
penalty). Three outcomes:
- **NEW SOTA (geo > 0.4152)**: worst-agent shaping helps; queue
  phi-max sweep {0.5, 2.0}.
- **PARITY (0.40 ≤ geo ≤ 0.4152)**: shaping doesn't help SOTA.
- **REGRESS (geo < 0.40)**: shaping disrupts balanced policy;
  R31 was correctly disabled.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-max 1.0 \
    --save-dir results/r221_w1_hreg_phimax1_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (SOTA at phi_max=0)
- R31 verdict (original max-disturbance shaping design)
- v4_config.py phi_max docstring
