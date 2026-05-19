# R205 verdict — cross-seed ensembles regress; "single beats ensemble" rule firmly holds

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for cross-seed-as-ensemble-axis
**Type**: research (eval-only)

## TL;DR

Two cross-seed ensembles at the new SOTA hyper (tau=0.005):
- W1 3-way {s50, s51, s54}: geo=**0.3927**
- W2 4-way (+R142 QR): geo=**0.4017**

Both below R201 single (0.4152) by 5.4% and 3.3% respectively. Even
viable-only cross-seed (no s49 collapse contamination) regresses the
ensemble. The s50 result (0.3481) drags the average down despite being
above the "collapse" threshold.

## Final ensemble registry (after R205)

| Ensemble | Components | geo | vs single SOTA 0.4152 |
|----------|------------|-----|------------------------|
| R201 single | hreg tau=0.005 s54 | **0.4152** | (ref) |
| R202 same-seed cross-algo | R201 + R142 + R143 + R100 | 0.4145 | -0.07% |
| R154 prev SOTA | R72_w4 + R142 + R143 + R100 | 0.4119 | -0.8% |
| R177 7-way max | (all) | 0.4124 | -0.7% |
| **R205 W2 cross-seed+algo** | 3 hreg-seeds + R142 | 0.4017 | -3.3% |
| **R205 W1 cross-seed** | s50/51/54 hreg | 0.3927 | -5.4% |

**Pattern is firmly established**: at this single-policy ceiling
(~0.415), no tested ensemble structure beats the single best policy.

## Mechanism (consistent with CLM-0325)

Cross-seed at viable seeds gives policies that are similar in profile
(all balanced after hreg regularization). Mean-averaging similar
policies dilutes rather than complements. The s50 result (0.348) is
the lowest constituent and disproportionately drags the mean.

## What's productive next

Single-axis hyper search exhausted on hreg path. Untested **structural**
axes that could yield SOTA improvements:
- Reward shaping overrides (phi_h, phi_d, phi_f)
- CTDE (--ctde flag, centralized critic at training)
- Communication failure robustness (--comm-fail)
- Smaller hidden size at hreg (h=32, 48)

R206 candidate: **hreg at s54 with --comm-fail 0.05** — tests SOTA
hyper under realistic deployment stress (5% comm-failure rate).
Paper-relevant: VSG controllers must work with imperfect grid comm.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

R205 cross-seed ensemble 全部低于 R201 single 0.4152:
- W1 3-way s50/51/54 = 0.3927 (-5.4%)
- W2 4-way + R142 = 0.4017 (-3.3%)

"Single beats ensemble" rule 实证完整 — viable-only seeds 也不行,
balanced policies 平均 = dilute. 这一致 with CLM-0325 ensemble theory.

**所有 ensemble 路径都已 test exhausted**:
- same-seed cross-algo: R154/R202 (-0.8%/-0.07%)
- offset-diversity: R197 (all -3-7%)
- cross-seed viable: R205 (-3-5%)

下一个 R206 = test SOTA hyper under comm-failure 5% — paper-relevant
robustness axis, 没测过。可能 reveal "SOTA 在 comm-failure 下 still
robust" 或者 "comm-failure 大改 SOTA"。

## Cross-references

- R201 (single SOTA)
- R202 (same-seed cross-algo)
- R154 / CLM-0295 (cross-seed with collapse contamination)
- CLM-0325 (ensemble theory)
