---
round: R246
state: active
opened: '2026-05-20'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R246 plan — scalar + only phi_abs at s50 (disambiguate R242 single-seed quirk vs real)

**Status**: ACTIVE
**Opened**: 2026-05-20
**Type**: research (autonomous loop, R242 follow-up)
**Driver**: R242 (scalar s51 + only phi_abs) = 0.3003, **-15.7% from
R154_w2 s51 baseline 0.3562**. First only-phi_abs run to break the
"universal vestigial" pattern. R246 tests scalar + only phi_abs at
**s50** — third seed for scalar. Resolves whether R242 is single-
seed RNG-basin quirk or real scalar-seed sensitivity.
**Parent**: R242 verdict (CLM-0400).

## TL;DR

Train td3_lstm scalar at s50 with --phi-h 0 --phi-d 0 --phi-f 0
(only phi_abs=50). Outcomes:
- **baseline-match (geo ≈ 0.39 ± 1.5%)**: R242 is s51-specific
  quirk; "universal vestigial" claim holds for 2-out-of-3 scalar
  seeds. Paper claim stays: inert in 3/4 cells.
- **drop matching R242 (geo ≈ 0.30, -15%)**: scalar is genuinely
  paper-term-sensitive across seeds. Paper claim hardens: "inert
  for hreg universal, scalar-seed-dependent".
- **collapse (geo < 0.10)**: scalar at s50 needs paper terms
  for training viability. Unexpected; would refute scalar+only-
  phi_abs trainability entirely.

## Methodology

```
LR=1e-4 python scripts/train.py --algo td3_lstm \
    --episodes 75 --seed 50 --hidden-size 64 --tau 0.005 \
    --normalize-actions --lstm-lr-warmup-eps 5 \
    --phi-h 0 --phi-d 0 --phi-f 0 \
    --save-dir results/r246_w1_scalar_onlyphiabs_s50
```

After training:
```
python scripts/score_run.py --label r246_w1_scalar_onlyphiabs \
    --ckpt-dirs results/r246_w1_scalar_onlyphiabs_s50 \
    --out-dir results/r246_w1_scalar_onlyphiabs_s50
```

## Decision tree

| R246 outcome | Paper claim 5 narrative |
|--------------|--------------------------|
| ≥ 0.38 | R242 是 s51 quirk; inert 3/4 cells holds, fooled by 1 outlier |
| 0.30 ± 0.03 | scalar genuinely seed-sensitive vs hreg seed-insensitive |
| < 0.10 | scalar+only-phi_abs is fragile, paper terms add training viability for scalar |

## Cross-references

- R242 (scalar s51 only phi_abs = 0.3003 — refutation outlier)
- R239 (scalar s54 only phi_abs = 0.3954 — baseline-matching)
- R241 (hreg s51 only phi_abs = 0.3895 — baseline-matching, hreg cross-seed)
- CLM-0400 (R242 partial-refutation claim)
- docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md
