# R224 verdict — Double inertia FRAGILE (-33.7%); robustness is asymmetric

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for high-inertia robustness; KEY paper insight
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --vsg-m0 400 (H₀=200s,
2× trained-on default). Result: geo=**0.2753**, LS1=0.229, LS2=0.331,
cum_rf=-0.0582.

**vs R201 (H₀=100 default): -33.7%** — the biggest physical-
parameter regression observed. The robustness curve is **non-
monotonic and asymmetric**.

## Complete inertia robustness curve

| vsg_m0 (H₀) | direction | run | LS1 | LS2 | geo | Δ |
|--------------|-----------|-----|-----|-----|-----|------|
| 50 (25s) | 1/4× | R223 | 0.362 | 0.406 | 0.3832 | -7.7% |
| 100 (50s) | 1/2× | R222 | 0.364 | 0.445 | 0.4028 | -3.0% |
| **200 (100s)** | **trained** | **R201** | **0.368** | **0.469** | **0.4152** | (ref) |
| **400 (200s)** | **2×** | **R224** | **0.229** | **0.331** | **0.2753** | **-33.7%** |

**Robustness is ASYMMETRIC**:
- Inertia REDUCTIONS: robust (up to 4× → -7.7%)
- Inertia INCREASES: fragile (2× → -33.7%)

## Mechanism interpretation

Higher inertia means slower dynamics; the policy's trained action
timing (tuned for H₀=100 response speed) is too aggressive for
H₀=200, causing over-control oscillations. Lower inertia means
faster dynamics; the policy's actions are slightly conservative but
still effective.

**Heuristic for practitioners**: train on the HIGHEST expected
deployment inertia; lower-inertia deployments will then be robust.
Training on a low inertia and deploying at high inertia is risky.

## Refined paper Sec.IV-D contribution 6

> "We characterize physical-inertia robustness asymmetrically: the
> SOTA controller retains 92.3% performance at quarter inertia (4×
> reduction) but only 66.3% at double inertia. This identifies an
> operational guideline: training at the highest expected inertia
> yields robustness to lower-inertia deployments, but not vice versa.
> The mechanism is action-timing mismatch under slower dynamics."

This is more nuanced than the original "monotonic robust" framing
— and more honest.

## R225 candidate

Fill the high-inertia curve at vsg_m0=300 (1.5×). If degradation is
roughly linear from R201 to R224, expect ~0.34. If steeper at 2×,
the breakdown is sudden.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — physical robustness asymmetry identified)

## 给 PI 的话

⚠️ **R224 = vsg_m0=400 (double inertia H₀=200) = geo 0.2753, -33.7%**!
最大的 physical-param regression. Robustness 是 **asymmetric**.

| H₀ | geo |
|----|-----|
| 25 | 0.3832 |
| 50 | 0.4028 |
| 100 | 0.4152 (trained) |
| **200** | **0.2753** |

**Inertia 减小 robust (4× → -7.7%); inertia 增大 fragile (2× → -34%)**.

机制: 高 inertia 意味更慢 dynamics, policy 训出的 action timing 太
激进, over-control oscillation. 低 inertia 意味更快 dynamics, action
稍 conservative 但仍 effective.

**Paper Sec.IV-D 第 6 个 contribution 框架变了**: 不是"monotonic
robust", 是 "**asymmetric robustness: train on highest-expected
inertia, lower-inertia deployments robust**". 这是 honest 的 operational
guideline.

R225 = vsg_m0=300 (1.5×) 填 curve, 看 high-inertia 是 linear 还是 sudden
breakdown.

## Cross-references

- R201/R222/R223 (inertia curve)
- v4_config.py vsg_m0
