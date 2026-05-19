---
round: R101
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R101 plan — Multi-seed MLP D3 redo: rigorous closure of CLM-0168 retraction

**Status**: DONE (W1 done in same turn)
**Opened**: 2026-05-19
**Driver**: [[CLM-0168]] retracted [[CLM-0163]]'s "γ=0.99 R²=−0.41" finding
as MLP regression noise (R96 same-ckpt re-run gave +0.659). To make the
retraction rigorous, run the regressor with 10 different torch RNG seeds
on the same data; report R² distribution per (γ, agent).
**Parent**: R96 / CLM-0168.

## TL;DR

Single SOTA rollout (R72_w4, LS1+LS2 deterministic, 400 records). Fit
each γ ∈ {0, 0.9, 0.99, 1.0} obs→return regressor + obs→action regressor
× 10 torch RNG seeds (also vary train/test split seed) × 4 agents =
200 fits. Report R² median + IQR per γ. Verdict: is the value-horizon
finding noise or signal?

## Result preview

See `verdict.md` for full numbers. Headline: γ=0.99 median R² = +0.643
(positive), CLM-0163 −0.41 was a left-tail outlier, CLM-0168 retraction
stands but value-horizon mismatch hypothesis is empirically dead.

## Cross-references

- [[CLM-0163]] (retracted; this round empirically demonstrates the
  retraction was warranted)
- [[CLM-0168]] (retraction claim, confirmed by R101)
- [[CLM-0169]] (this round's finding)
