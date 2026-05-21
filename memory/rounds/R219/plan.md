---
round: R219
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R219 plan — paper Eq.14 + phi_abs=50 (paper-strict + V4 patch combined)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, paper-faithful + patch composition)
**Driver**: R218 showed paper Eq.14 alone fails (phi_abs=0 collapse).
R219 = paper Eq.14 WEIGHTS (phi_h=1, phi_d=1, phi_f=100) WITH the
phi_abs=50 patch. If geo ≥ 0.40, then **"paper-faithful + V4 patch =
SOTA"** is the cleanest publication recipe. If lower than R201 (V4-
default + phi_abs=50), then V4's R18 rescale is also load-bearing.
**Parent**: R218, R201, R214 verdicts.

## TL;DR

Train td3_lstm_hreg λ=0.002 tau=0.005 at s54 with --phi-h 1 --phi-d 1
--phi-f 100 --phi-abs 50. Three outcomes:
- **NEW BEST (geo > 0.4152)**: paper weights + patch is the optimal
  recipe; R201 was suboptimal due to V4 rescale.
- **MATCHES R201 (0.40 ≤ geo ≤ 0.4152)**: paper-faithful recipe works
  with patch; cleanest publication recipe.
- **REGRESS (geo < 0.40)**: paper-original weights interact poorly
  with phi_abs=50; V4 rescale is also load-bearing.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --phi-f 100 --phi-h 1 --phi-d 1 --phi-abs 50 \
    --save-dir results/r219_w1_hreg_paperstrict_plus_phiabs50_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R201 (V4 default + phi_abs=50 = 0.4152)
- R218 (paper-strict + phi_abs=0 = collapse)
- R214/R215/R216/R217 (phi_abs sweep with V4 default)
