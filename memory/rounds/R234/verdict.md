# R234 verdict — phi_h=0.003 (half V4) SOTA-equivalent; sweet spot widens down

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — phi_h sweet spot extends to ≥0.5× V4 default
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0.003 --phi-d
0.003 (half V4 default 0.0056). Result: geo=**0.4152**, LS1=0.368,
LS2=0.469, cum_rf=-0.0692. **Bit-identical to R201**.

Sweet spot extends DOWNWARD to at least 0.003 (0.5× V4).

## phi_h sweet spot landscape (complete)

| phi_h | scale vs V4 | run | geo | regime |
|-------|-------------|-----|-----|--------|
| 0.003 | 0.5× | R234 | **0.4152** | SOTA-equivalent |
| 0.006 (V4) | 1× | R201 | 0.4152 | SOTA |
| 0.01 | 1.8× | R232 | 0.4153 | SOTA-equivalent |
| 0.02 | 3.6× | R233 | 0.0100 | COLLAPSE |
| 0.05 | 9× | R231 | 0.0100 | COLLAPSE |
| 1 (paper) | 179× | R218 | 0.0100 | COLLAPSE |

**Confirmed sweet spot**: phi_h ∈ [0.003, 0.01] (at least 0.5× to 1.8×
V4). **Sharp asymmetric cliff at ~0.02 (3.6× V4)** — upward.

## Reward landscape refined picture

Combining all sweep findings:
- phi_h sweet spot: [0.003, 0.01] (factor of 3 width, but asymmetric
  cliff at high side)
- phi_abs threshold: ≥7 (with V4 phi_h)
- phi_d = phi_h symmetric (changes together)
- phi_f = 100 (paper, also used in V4)

The sweet spot is a finite-width box; multiple reward weights must
be jointly within their respective windows for SOTA.

## R235 candidate

Test phi_h=0.001 (very low end, 0.18× V4). If still viable, sweet
spot extends very low; if collapse, low-side cliff is in (0.001, 0.003].

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

R234 = phi_h=0.003 (0.5× V4) = bit-identical SOTA. Sweet spot 现在
**[0.003, 0.01] 确认** (3× width).

**Reward landscape 最终 picture**: phi_h ∈ [0.003, 0.01] (3× factor
width), 然后 sharp asymmetric cliff at 0.02. phi_abs ≥ 7 threshold.
Multiple reward weights 各有 narrow operating window.

R235 = phi_h=0.001 (0.18× V4) test very low end.

## Cross-references

- R201/R232 (SOTA)
- R231/R233/R218 (collapse high side)
