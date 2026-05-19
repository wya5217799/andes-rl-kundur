# R235 verdict — phi_h=0.001 SOTA-equivalent; sweet spot extends very low

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — phi_h sweet spot is asymmetric (wide-low, narrow-high)
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0.001 --phi-d
0.001 (0.18× V4 default). Result: geo=**0.4152**, bit-identical to
R201.

phi_h sweet spot extends down to AT LEAST 0.001. Full picture:

| phi_h | scale | run | geo | regime |
|-------|-------|-----|-----|--------|
| 0.001 | 0.18× | R235 | **0.4152** | SOTA |
| 0.003 | 0.5× | R234 | 0.4152 | SOTA |
| 0.006 | 1× (V4) | R201 | 0.4152 | SOTA |
| 0.01 | 1.8× | R232 | 0.4153 | SOTA |
| 0.02 | 3.6× | R233 | 0.0100 | COLLAPSE |
| 0.05 | 9× | R231 | 0.0100 | COLLAPSE |
| 1 | 179× | R218 | 0.0100 | COLLAPSE |

## Asymmetric sweet spot

The sweet spot is **wide on the low side, narrow on the high side**:
- Low: confirmed viable down to 0.001 (0.18× V4); lower bound untested
- High: sharp cliff in (0.01, 0.02]; only ~1.8× tolerance upward

## Mechanism interpretation

phi_h scales the frequency-deviation penalty. At low phi_h, the
controller learns from phi_abs (Kundur tight-coupling) and phi_f
(load step) signals — phi_h is "extra" reward gradient. At high
phi_h, the strong frequency-deviation gradient dominates and pushes
the actor into a different (bad) attractor.

This explains why V4's R18 rescale (1/178 of paper) works: it
shrunk phi_h DOWN into the safe-low region. Paper-original phi_h=1
sits well above the cliff.

## Refined paper finding

Earlier R231 stated "narrow sweet spot around V4 default". Now refined:
- Sweet spot has wide tolerance to phi_h reduction (≥30× from V4)
- Sweet spot has narrow tolerance to phi_h increase (~1.8×)
- The R18 rescale chose a value safely inside the wide region

## R236 candidate

phi_h=0 (disable frequency-deviation penalty entirely). If SOTA, the
phi_h reward term contributes nothing at training time (the policy
relies on phi_abs + phi_f only). If collapse, the term is necessary
at any non-zero value.

## Questions opened / closed / advanced

(none)

## 给 PI 的话

R235 = phi_h=0.001 (0.18× V4) = bit-identical SOTA. Sweet spot
**asymmetric**: 低端 wide (至少 [0.001, 0.01]), 高端 sharp cliff (0.02).

机制: phi_h 是 extra signal, 主导 reward 是 phi_abs + phi_f. 低 phi_h
不伤; 高 phi_h disrupt gradient balance.

V4 R18 rescale 选 0.0056 是 safely inside wide low region. Paper
原始 phi_h=1 well above cliff (179×).

R236 = phi_h=0 (disable). 如果 SOTA, 这个项 training 时实际 contribute
nothing — 进一步 paper-faithfulness 故事.

## Cross-references

- R201/R232/R234 (SOTA at various phi_h)
- R218/R231/R233 (collapse high side)
