# R230 verdict — Scalar+gamma=0.95 = baseline; gamma not load-bearing for any algo

**Date**: 2026-05-20
**Status**: CLOSED-NEUTRAL — gamma-insensitivity is env property, not hreg-specific
**Type**: research

## TL;DR

Trained `td3_lstm` scalar at s54 with tau=0.005 + --gamma 0.95.
Result: geo=**0.3905**, LS1=0.354, LS2=0.431, cum_rf=-0.0680.

**Essentially identical to R72_w4 baseline (gamma=0.99): 0.391**.
The hypothesis "hreg provides gamma-robustness" is REFUTED. Both
algos tolerate gamma deviations equally.

## Gamma comparison across algos

| algo | gamma=0.95 | gamma=0.99 | gamma=0.999 |
|------|------------|-----------|--------------|
| scalar | 0.3905 (R230) | 0.391 (R72_w4) | (untested) |
| hreg | 0.4133 (R229) | 0.4152 (R201) | 0.4152 (R213) |

Both algos: gamma=0.95 is -0.5% from gamma=0.99 (within noise).
Gamma-insensitivity is a **property of the env/task**, not an
algorithm-specific feature.

## Saturation continues

This is yet another confirmation that the SOTA hyper is in a flat
basin wrt most axes. The relevant load-bearing axes (λ, horizon,
hidden, phi_abs, seed, offset, training-time vsg_m0) are
comprehensively characterized.

## R231 candidate

Untested combination: phi_h=0.05 (10× V4 default 0.0056, still 1/20
paper). Could reveal a new reward landscape basin.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

R230 = scalar + gamma=0.95 = 0.3905 ≈ R72_w4 baseline. **gamma 不
是 hreg-specific 的 robustness**, 两种算法都 gamma-insensitive.

Cross-algo gamma table 显示 hreg / scalar 在 gamma 上行为一致, 都
flat ±0.5% within noise.

R231 候选 = phi_h=0.05 (10× V4 default 中间 magnitude).

## Cross-references

- R229 (hreg gamma=0.95)
- R72_w4 (scalar baseline)
