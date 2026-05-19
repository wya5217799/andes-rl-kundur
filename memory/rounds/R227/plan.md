---
round: R227
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R227 plan — SOTA hyper at --vsg-d0 sweep (independent physical axis + R222-R226 interp fix)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, physical-param damping axis)
**Driver**: R222-R226 inertia curve is **training-time** difficulty
not deployment robustness (--vsg-m0 sets env at TRAIN AND EVAL).
Interpretation fix: the H₀=200 collapse is "this env config is harder
to train at SOTA hyper", not "policy fragile to inertia changes".

R227 = independent physical-param axis: --vsg-d0 (damping coefficient
default). Tests if SOTA hyper trains equally well across damping
configurations.

**Parent**: R201 (default damping SOTA), R222-R226 (inertia curve).

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --vsg-d0 50 (half of
default 100). Tests if SOTA hyper is sensitive to damping coefficient
reduction.

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-d0 50 \
    --save-dir results/r227_w1_hreg_d0_50_s54
```

Default vsg_d0=100 per v4_config.py. R227 uses 50 (half).

## Note on R222-R226 interpretation correction

The inertia curve I built (R222-R226 + R201/R224) is the **training-
difficulty curve at varying physical inertia**, not robustness of a
single trained policy. The H₀=200 result (R224 = 0.275) means
"SOTA hyper is hardest to train at H₀=200", not "trained policy is
fragile to H₀=200 deployment". For true deployment robustness, would
need to load R201 ckpt and eval it under different vsg_m0 values
(requires eval script with env-override capability).

Despite the misinterpretation, the training-difficulty curve is still
a useful paper finding: the SOTA hyper is robust to **training at**
inertia in [0.25×, 1.75×] but cannot train successfully at 2× inertia
within 75 episodes. This relates to learning dynamics, not deployment.

## Gate

- VIABLE (geo ≥ 0.35): SOTA hyper handles damping change
- COLLAPSE (geo < 0.20): damping is load-bearing too

## Cross-references

- R201 (SOTA at default damping)
- R222-R226 (inertia training-difficulty curve)
- v4_config.py vsg_d0
