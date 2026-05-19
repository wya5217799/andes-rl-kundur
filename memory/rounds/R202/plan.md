---
round: R202
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R202 plan — ensemble {R201, R142, R143, R100} replace R72_w4 in R154 SOTA

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, ensemble swap test)
**Driver**: R201 (new single-policy SOTA 0.4152) is strictly better
than R72_w4 (0.391) on geo. R154 4-way SOTA was {R72_w4, R142, R143,
R100} = 0.4119. Swapping R72_w4 → R201 should at minimum match (if
ensemble is dominated by R201) or potentially exceed 0.4119 if the
upgrade lifts the ensemble.

**Parent**: R154 (CLM-0295 ensemble SOTA), R201 (new single SOTA).

## TL;DR

Eval 4-way ensemble {R201, R142, R143, R100} mean-aggregation,
suffixes=best. Compare to:
- R154 SOTA: 0.4119 (with R72_w4 instead of R201)
- R177 7-way max diversity: 0.4124
- R201 single: 0.4152

Three outcomes:
- **NEW ENSEMBLE SOTA (geo > 0.4152)**: ensemble exceeds R201 single;
  new headline ensemble number.
- **PARITY (0.4119 ≤ geo ≤ 0.4152)**: ensemble inherits R201's
  improvement but doesn't add. R201 single remains the cleanest claim.
- **REGRESS (geo < 0.4119)**: R201's better balance reduces ensemble
  diversity benefit (same pattern as R170 swap in CLM-0325 showed).

## Methodology

```
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r201_w1_hreg_tau005_s54 \
                results/r142_w1_qr51_s54 \
                results/r143_w1_qr51_s54_fixed \
                results/r100_w1_hreg_lambda0p01_s54 \
    --suffixes best best best best --agg mean \
    --label r202_w1_swap_r72w4_to_r201 \
    --out-dir results/r202_ensemble
```

ANDES eval ~5 min.

## Cross-references

- R201 verdict (new SOTA 0.4152)
- R154 / CLM-0295 (4-way ensemble SOTA 0.4119)
- R177 verdict (7-way diversity 0.4124, R174 single beats)
- CLM-0325 (R170 swap result, complementary-asymmetric ensemble theory)
