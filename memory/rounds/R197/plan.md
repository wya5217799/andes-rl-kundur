---
round: R197
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R197 plan — multi-offset ensemble eval (novel: offset-diversity as ensemble axis)

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, eval-only)
**Driver**: R196 completed 2x2 algo×offset grid showing hreg cross-
offset stable. R197 tests a novel ensemble axis: combine the SAME
algorithm at DIFFERENT offsets. If RNG-path diversity creates
complementary policies, ensemble might beat single-(seed, offset)
maxima.

## Two ensembles to evaluate (eval only, no training)

### W1 — scalar offset-diversity 3-way
Ensemble of {R72_w4 (s54, off=0), R196 (s54, off=50), R192 (s54, off=100)}.
- Single bests: 0.391, 0.3983, 0.2844
- Mean-aggregation prediction: if independent → ~0.36-0.40; if
  complementary → could approach hreg single-best 0.4139.

### W2 — hreg offset-diversity 3-way
Ensemble of {R174 (off=0), R194 (off=50), R193 (off=100)}.
- Single bests: 0.4139, 0.3882, 0.3875
- Mean-aggregation prediction: if independent → ~0.40; if
  complementary → potentially > 0.4139 (new SOTA).

### W3 — hreg cross-offset + cross-algo
Combine W2 hreg-offset triplet with R142 (QR), R143 (QR-fixed) for
5-way max diversity.

## Gate

- **W2 > 0.4139**: novel offset-diversity ensemble beats single-RNG-path
  SOTA. **New paper finding**: "Offset-diversity is an ensemble axis
  orthogonal to algo-diversity." Queue R198 (more ensembles).
- **All W1/W2/W3 ≤ 0.41**: offset-diversity is not productive; abandon.
- **W3 > W2 and > 0.4139**: offset + algo diversity combine; new
  multi-axis ensemble theory.

## Methodology

```
# W1 scalar 3-way
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r72_w4_lstm_tau001_warmup5_s54 \
                results/r196_w1_scalar_s54_offset50 \
                results/r192_w1_scalar_s54_offset100 \
    --suffixes best best best --agg mean \
    --label r197_w1_scalar_offset_div \
    --out-dir results/r197_ensemble

# W2 hreg 3-way
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r174_w1_hreg_lambda0p002_s54 \
                results/r194_w1_hreg_s54_offset50 \
                results/r193_w1_hreg_s54_offset100 \
    --suffixes best best best --agg mean \
    --label r197_w2_hreg_offset_div \
    --out-dir results/r197_ensemble

# W3 hreg-offset + cross-algo 5-way
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r174_w1_hreg_lambda0p002_s54 \
                results/r194_w1_hreg_s54_offset50 \
                results/r193_w1_hreg_s54_offset100 \
                results/r142_w1_qr51_s54 \
                results/r143_w1_qr51_s54_fixed \
    --suffixes best best best best best --agg mean \
    --label r197_w3_hreg_offset_algo \
    --out-dir results/r197_ensemble
```

ANDES eval ~5 min each, 3 evals = ~15 min total.

## Cross-references

- R196 verdict (2x2 grid)
- R154 (4-way SOTA 0.4119)
- R177 (7-way max diversity 0.4124)
- CLM-0295 (R154 ensemble theory)
