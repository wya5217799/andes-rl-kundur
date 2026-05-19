---
round: R71
state: active
opened: '2026-05-18'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R71 plan — paper_grade_axes v3.0→v3.1 (multiplicative gating) + further LSTM sweep

**Date**: 2026-05-18
**Type**: ranker refinement + continued LSTM hyper sweep
**Wall budget**: ~1.5 hr

## Trigger

R70 picked R68 W2 s51 as canonical best for paper figures despite R69 W3 s50
having higher v3 numeric (0.5474 vs 0.5329). User asked "图好看是有效标准吗"
and "优化评估". Identified v3.0 dilution problem: geo_mean lets strong
continuous axes (1-8) hide weak gating axes (9-11).

## v3.1 design (CLM-0119)

```
overall_v3.1 = geo_mean(axes 1-8) × min(axes 9, 10, 11)
```

Multiplicative gating ensures any single ugly gating axis caps overall.
Matches paper-figure intuition "any one ugly axis = ugly paper figure".

## Continued sweep (W1-W6 under v3.1 guidance)

- W1: tau+warmup=5 s53 (4-seed expansion of v3.1 family SOTA)
- W2: tau+warmup=10 s50 (gap fill 5↔20)
- W3: tau+warmup=15 s50 (gap fill)
- W4: tau+warmup=25 s50 (probe right of peak)
- W5: tau+warmup=30 s50 (further probe)
- W6: tau+warmup=20 s53 (s53 verify with peak warmup)
