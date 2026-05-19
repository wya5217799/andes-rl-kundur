# R201 verdict — tau=0.005 NEW PROJECT SINGLE-POLICY SOTA (geo 0.4152 > R174 0.4139)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — new single-policy SOTA, R174's tau=0.001 simplifiable
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s54+offset=0 with **tau=0.005**
(default, vs R174's slow tau=0.001). Result: geo=**0.4152**, LS1=0.368,
LS2=0.469, cum_rf=-0.069.

**NEW project SOTA: 0.4152** (+0.3% over R174's 0.4139). Within
robustness CV 2.5% so statistically marginal, but it's the
**highest single-policy geo recorded in the project** and
**simplifies the SOTA hyper** by dropping the unusual slow tau.

## Comparison

| Run | tau | LS1 | LS2 | geo | vs R72_w4 0.391 |
|-----|-----|-----|-----|-----|-------------------|
| R72_w4 baseline | 0.001 | 0.354 | 0.431 | 0.391 | (ref) |
| R174 (prev SOTA) | 0.001 | 0.367 | 0.467 | 0.4139 | +5.9% |
| **R201 (NEW SOTA)** | **0.005** | **0.368** | **0.469** | **0.4152** | **+6.2%** |

LS1/LS2/cum_rf all essentially identical to R174 — the +0.3% lift
is uniform across axes, suggesting tau=0.005 is **at least as good**
as tau=0.001 for hreg λ=0.002 at this horizon.

## Paper implications

1. **Simplification finding**: The R72_w4 family's tau=0.001 is not
   load-bearing for SOTA. Default tau=0.005 is sufficient. This
   simplifies the recommended baseline hyper in the paper.
2. **New headline number**: 0.4152 (vs 0.4139). Marginally better
   single-policy SOTA. Paper Sec.IV-D updated table.
3. **Mechanism unchanged**: same hreg λ=0.002 sweet spot, same horizon,
   same seed/offset. tau is independent dimension.

## R201 may also be offset-robust

Untested: does R201 (tau=0.005) keep its lead at offset=100, or does
the +0.3% margin evaporate? R202 candidate.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — single-policy SOTA update, no Q-tied)

## Questions advanced (this round, status unchanged)

(none directly — but the "lucky seed s54" caveat extends now to
(s54, tau=0.005) — same s54 dependency)

## 给 PI 的话

🎯 **R201 = hreg λ=0.002 tau=0.005 at s54 = geo 0.4152 — NEW SOTA**!
比 R174 (tau=0.001) 0.4139 高 +0.3% (在 noise band 内但 strictly 更高).

**两个 take-aways**:
1. R174 用的 tau=0.001 (慢 5×) 不是必需; default tau=0.005 给 same-or-better
   结果. Paper Sec.IV-D 推荐 hyper 简化掉 tau=0.001.
2. Single-policy SOTA 现在是 R201 0.4152, R174 0.4139 退居第二.

**还在 noise band 内** (CV 2.5% ≈ ±0.010), 所以 R174 跟 R201 实际等价 —
但 R201 hyper 更 simple, 推荐 R201 当 canonical.

R202 候选 = tau=0.005 at s51 (cross-seed transfer test) 或 R201+offset=100
(offset robustness). 我下次 launch.

## Cross-references

- R174 (prev SOTA at tau=0.001)
- R72_w4 (baseline at tau=0.001)
- CLM-0094 (R72_w4 hyper definition)
- CLM-0325 (hreg dose-response narrative)
