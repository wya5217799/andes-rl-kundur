# R202 verdict — R201-anchored 4-way ensemble = 0.4145, new ENSEMBLE SOTA (still < R201 single)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE for ensemble SOTA update, NEGATIVE for ensemble-beats-single
**Type**: research (eval-only)

## TL;DR

Ensemble {R201 (new single SOTA), R142, R143, R100} mean-aggregation:
geo=**0.4145**, LS1=0.369, LS2=0.465.

| Run | components | geo |
|-----|------------|-----|
| **R201 single** | hreg λ=0.002 tau=0.005 s54 | **0.4152** |
| **R202 4-way** | R201 + R142 + R143 + R100 | **0.4145** (NEW ensemble SOTA) |
| R154 4-way | R72_w4 + R142 + R143 + R100 | 0.4119 |
| R177 7-way | (all variants) | 0.4124 |

R202 beats R154 (previous ensemble SOTA) by **+0.6%**. But R201 single
still beats R202 ensemble by 0.07% (within noise). The "single beats
all ensembles" pattern from R177 continues to hold — at finer
granularity now.

## Why ensemble still loses to single

Same mechanism as CLM-0325: R201 is balanced-strong (LS1=0.368,
LS2=0.469); averaging with R142/R143/R100 (slightly different but
not asymmetrically complementary to R201) dilutes the LS1+LS2 peak.
Ensemble lift requires asymmetric complementarity that R201's
balanced profile reduces.

## Project SOTA registry update

After R201 + R202:
- **Single-policy SOTA**: R201 0.4152 (hreg λ=0.002, tau=0.005, s54)
- **Ensemble SOTA**: R202 0.4145 (4-way with R201 as anchor)
- **Best-balanced**: same R201 (LS1=0.368, LS2=0.469)
- **Best LS2 single**: R169 (λ=0.005) LS2=0.477 but lower geo
- **2.13× advantage** vs R85 droop classical baseline 0.197

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — both single and ensemble SOTAs updated)

## 给 PI 的话

R202 4-way ensemble {R201, R142, R143, R100} = geo **0.4145** —
**new ensemble SOTA** (超 R154 0.4119 by +0.6%), 但仍 < R201 single
0.4152 by 0.07% (noise band).

"Single beats ensemble" pattern hold — R201 balanced policy 在
averaging 时被 dilute.

**项目 SOTA 双更新**:
- Single: R201 0.4152
- Ensemble: R202 0.4145

R203 候选: R201 hyper (tau=0.005) at s51 — 测 cross-seed transfer
of new SOTA hyper. 如果 s51 也 +0.3% (vs R181 0.389 → ~0.395), 新 hyper
is seed-universal. 我下次 launch.

## Cross-references

- R201 verdict (single SOTA 0.4152)
- R154 / CLM-0295 (R72_w4-anchored 4-way 0.4119)
- R177 (7-way 0.4124, single beats ensemble)
- CLM-0325 (R170 swap ensemble theory)
