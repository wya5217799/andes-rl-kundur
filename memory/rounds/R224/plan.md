---
round: R224
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R224 plan — SOTA hyper at --vsg-m0 400 (H₀=200, double inertia, symmetric extreme)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, physical-param symmetry)
**Driver**: R222/R223 showed SOTA robust at half/quarter inertia.
Symmetric test: double inertia. Higher inertia = slower dynamics =
EASIER for the controller in principle, so expect ≥ R201 SOTA.

## TL;DR

Train td3_lstm_hreg SOTA hyper at s54 with --vsg-m0 400 (H₀=200,
2× default). Three outcomes:
- **HIGHER (geo > 0.4152)**: monotonic improvement with inertia;
  doubled inertia gives easier control surface.
- **PARITY (0.40 ≤ geo ≤ 0.4152)**: equally robust at high inertia.
- **REGRESS (geo < 0.40)**: higher inertia surprisingly harder
  (different dynamics regime, unexpected).

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --vsg-m0 400 \
    --save-dir results/r224_w1_hreg_m0_400_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (vsg_m0=200 default SOTA 0.4152)
- R222 (vsg_m0=100 = 0.4028)
- R223 (vsg_m0=50 = 0.3832)
