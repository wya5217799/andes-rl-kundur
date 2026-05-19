---
round: R209
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R209 plan — scalar (NO hreg) at s54 + comm-fail=0.50 (isolate hreg's role in robustness)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, robustness control)
**Driver**: R208 showed hreg+comm-fail=50% gives 0.4009 (only -3.4%
from perfect-comm SOTA). Is this hreg-specific or just an LSTM
property? R209 = scalar (no hreg) at the same comm-fail rate.
**Parent**: R208 verdict, R72_w4 baseline.

## TL;DR

Train `td3_lstm` scalar λ=0 at s54 with tau=0.005, --comm-fail 0.50.
Three outcomes:
- **SCALAR ALSO ROBUST (geo ≥ 0.30)**: robustness is an LSTM
  architecture property; hreg merely adds the +0.3% lift.
- **SCALAR PARTIAL (0.15 ≤ geo < 0.30)**: hreg buffers but isn't sole
  cause of robustness.
- **SCALAR COLLAPSE (geo < 0.15)**: **hreg is the sole mechanism for
  comm-fail robustness**. Paper claim: hreg required for deployment.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 54 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --comm-fail 0.50 \
    --save-dir results/r209_w1_scalar_commfail050_s54
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R208 (hreg + 50% comm-fail = 0.4009)
- R201 (hreg + 0% = 0.4152)
- R72_w4 baseline (scalar + 0% = 0.391)
- R192 (scalar + offset=100 hurt, -27%)
