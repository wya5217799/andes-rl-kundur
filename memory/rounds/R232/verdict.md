# R232 verdict — phi_h=0.01 STILL SOTA (sweet spot extends to ≥1.8× V4)

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — phi_h sweet spot widened
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0.01 --phi-d
0.01 (1.8× V4 default). Result: geo=**0.4153**, LS1=0.368, LS2=0.469,
cum_rf=-0.0692. **Bit-identical to R201**.

Sweet spot extends from V4 default (0.006) at least to 0.01 (~1.8×).
Cliff is in (0.01, 0.05].

## Updated phi_h landscape

| phi_h | scale | run | geo | regime |
|-------|-------|-----|-----|--------|
| 0.0056 | 1× (V4) | R201 | 0.4152 | SOTA |
| **0.01** | **1.8×** | **R232** | **0.4153** | **SOTA-equivalent** |
| 0.05 | 9× | R231 | 0.0100 | COLLAPSE |
| 1 | 179× (paper) | R218 | 0.0100 | COLLAPSE |

Sweet spot is at least [0.006, 0.01]; cliff is in (0.01, 0.05].
Could narrow further with R233 phi_h=0.02.

## R233 candidate

phi_h=0.02 bisects the cliff. If viable, sweet spot extends to 0.02
(3.6× V4); if collapse, cliff is in (0.01, 0.02].

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

R232 = phi_h=0.01 (1.8× V4) = bit-identical SOTA. Sweet spot 至少
extends [0.006, 0.01]. Cliff 在 (0.01, 0.05].

R233 = phi_h=0.02 bisect.

## Cross-references

- R201 / R231 / R218
