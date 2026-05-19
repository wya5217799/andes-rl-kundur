---
round: R205
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R205 plan — cross-seed ensemble eval {R201, R203, R204} all tau=0.005

**Status**: ACTIVE
**Opened**: 2026-05-19
**Type**: research (autonomous loop, eval-only)
**Driver**: R201, R203, R204 form a clean 3-seed set at the new SOTA
hyper. R154 cross-seed ensemble was tainted by R72_w4 s49 collapse;
this set has only viable seeds (s50, s51, s54). Test if cross-seed
diversity at viable-only seeds gives ensemble lift.
**Parent**: R201, R203, R204 verdicts; CLM-0325 (cross-seed theory).

## TL;DR

Eval mean-aggregation ensembles:
- **W1 3-way cross-seed** {R201 s54, R203 s51, R204 s50}
- **W2 4-way cross-seed + cross-algo** add R142 (QR critic, s54)

Compare to:
- R201 single (s54): 0.4152
- R202 4-way same-seed cross-algo: 0.4145
- R154 4-way (with s49 contamination): 0.4119

Three outcomes:
- **NEW SOTA (geo > 0.4152)**: cross-seed at viable-only is productive;
  diversity beats single-seed peak. New paper Sec.IV-D finding.
- **PARITY (0.40 ≤ geo ≤ 0.4152)**: cross-seed dilutes, single still
  wins.
- **REGRESS (geo < 0.40)**: weak seed (s50 = 0.348) drags ensemble
  down; cross-seed averaging hurts when seeds differ widely.

## Methodology

```
# W1 — 3-way cross-seed at tau=0.005
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r201_w1_hreg_tau005_s54 \
                results/r203_w1_hreg_tau005_s51 \
                results/r204_w1_hreg_tau005_s50 \
    --suffixes best best best --agg mean \
    --label r205_w1_cross_seed_tau005 \
    --out-dir results/r205_ensemble

# W2 — 4-way add R142 QR critic at s54
python scripts/eval_ensemble.py \
    --ckpt-dirs results/r201_w1_hreg_tau005_s54 \
                results/r203_w1_hreg_tau005_s51 \
                results/r204_w1_hreg_tau005_s50 \
                results/r142_w1_qr51_s54 \
    --suffixes best best best best --agg mean \
    --label r205_w2_cross_seed_plus_qr \
    --out-dir results/r205_ensemble
```

ANDES eval ~10 min total.

## Cross-references

- R201, R203, R204 verdicts
- R202 (same-seed cross-algo SOTA ensemble 0.4145)
- R154 / CLM-0295 (cross-seed result with s49 contamination)
- CLM-0325 (ensemble complementarity theory)
