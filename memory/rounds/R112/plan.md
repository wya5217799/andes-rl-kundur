---
round: R112
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R112 plan — Warm-h_0 environment-side test: does CLM-0188 Q-lift help eval?

**Status**: DONE
**Opened**: 2026-05-19
**Driver**: User "继续研究, 一直干活, 别让我提醒, 优化agent". [[CLM-0188]]
(R104) found 9/9 LSTM ckpts have universal step-0 Q-side architectural
slack from warm-h_0 grad-ascent. No one tested whether it ACTUALLY
helps env-side 6-axis evaluation. R112 closes that gap.
**Parent**: R104 / CLM-0188.

## TL;DR

Real env reset, capture obs_0; grad-ascent (h_0, c_0) per agent to
maximise critic Q (R99/R104 recipe); use these warmed inits at episode
start; run LS1+LS2 deterministic; compare 6-axis geo vs zero-h
baseline. ~2 min wall, 1 ANDES slot.

If geo lifts ≥ +0.05 → warm-h_0 is a real agent optimisation;
R113 = learned h_init MLP.
If geo neutral → R104 Q-side is forensic curiosity.
If geo drops → step-0 saturation hurts dynamics; R113 needs norm constraint.

## Result preview

See verdict.md. Headline: **geo -0.37 catastrophic, cum_rf +0.037
improvement** — the two metrics disagree in sign. R104 warm-h_0 lever
is cum_rf-positive but geo-negative. Naive warm-h_0 ruled out for
6-axis optimisation. [[CLM-0204]] records the finding.

## Cross-references

- [[CLM-0188]] (R104 Q-side lift; this round's premise under test)
- [[CLM-0204]] (this round's finding)
- [[CLM-0200]] (synthesis updates after R112)
