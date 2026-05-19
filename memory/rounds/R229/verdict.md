# R229 verdict — gamma=0.95 only -0.5% (sweet spot ≥0.99)

**Date**: 2026-05-20
**Status**: CLOSED-NEUTRAL — gamma curve characterized
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --gamma 0.95. Result:
geo=**0.4133**, LS1=0.368, LS2=0.465, cum_rf=-0.0692. **vs R201
(gamma=0.99): -0.5% only**.

## Complete gamma sweep

| gamma | run | LS1 | LS2 | geo |
|-------|-----|-----|-----|-----|
| 0.95 | R229 | 0.368 | 0.465 | 0.4133 |
| **0.99** | **R201** | **0.368** | **0.469** | **0.4152** |
| 0.999 | R213 | 0.368 | 0.469 | 0.4152 |

gamma is **flat from 0.99 to 0.999** (bit-identical) but matters tiny
bit at 0.95 (-0.5%, mainly LS2 drop). Sweet spot is ≥0.99.

## Summary updated

The full gamma curve confirms saturation: only at unusually low
gamma does any per-axis sensitivity emerge, and even then within
±1% (eval noise).

## R230 candidate

Test if gamma-insensitivity is hreg-specific. R230 = scalar (no hreg)
at gamma=0.95. If scalar is more gamma-sensitive than hreg, that's
another robustness contribution.

## Questions opened / closed / advanced

(none)

## 给 PI 的话

R229 = gamma=0.95 = 0.4133 (-0.5%). Sweet spot 是 ≥0.99 (R201/R213
bit-identical). gamma 在 [0.99, 0.999] flat, 0.95 略低 0.5%.

R230 候选 = scalar + gamma=0.95 测 hreg specificity of gamma-insensitivity.

## Cross-references

- R201 (gamma=0.99 SOTA)
- R213 (gamma=0.999 bit-identical)
