# R233 verdict — phi_h=0.02 COLLAPSE; cliff is narrow at (0.01, 0.02]

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — phi_h cliff bracket narrowed to 0.01-0.02
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --phi-h 0.02 --phi-d
0.02 (3.6× V4 default). Result: geo=**0.0100**, LS1=**0.000**,
LS2=0.003, cum_rf=-0.1684. **COLLAPSE** (bit-identical to R231 /
R218 / R214).

## Updated phi_h landscape (high side)

| phi_h | scale vs V4 | run | geo | regime |
|-------|-------------|-----|-----|--------|
| 0.006 (V4) | 1× | R201 | 0.4152 | SOTA |
| 0.01 | 1.8× | R232 | 0.4153 | SOTA-equivalent |
| **0.02** | **3.6×** | **R233** | **0.0100** | **COLLAPSE** |
| 0.05 | 9× | R231 | 0.0100 | COLLAPSE |
| 1 (paper) | 179× | R218 | 0.0100 | COLLAPSE |

**Cliff is in (0.01, 0.02]** on the high side — sharp transition,
only ~1.8× tolerance from V4 default.

## Reward sensitivity story (cumulative)

Two sharp cliffs identified for the V4 ANDES reward landscape:
- **phi_abs threshold** (R214-R217): below ~7, full collapse; above
  ~10, near-SOTA
- **phi_h cliff** (R231-R233): tolerates ~1.8× upward scaling from V4
  default, then sharp collapse

Both cliffs converge on the same LS1=0 attractor (bit-identical
collapse output across all "below threshold" or "above ceiling"
configurations). This suggests **one universal attractor** that
multiple reward-shaping perturbations land in.

## R234 candidate

Test LOW side: phi_h=0.003 (half V4 default). If viable, sweet spot
is asymmetric or wide on the low side. If collapse, sweet spot is
narrow ~[V4_default, ~0.01] only.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

R233 = phi_h=0.02 (3.6× V4) = COLLAPSE. Cliff 是 **(0.01, 0.02]**.

**Reward landscape 两个 sharp cliffs**:
- phi_abs threshold ~7 (R215-R217)
- phi_h cliff ~1.8× V4 default (R231-R233)

两 cliff 都 land 在 same LS1=0 attractor (bit-identical collapse).
**很可能 same universal attractor**, 多种 reward perturbation 都掉进去.

R234 = phi_h=0.003 (半 V4) test LOW side.

## Cross-references

- R201/R232 (sweet spot)
- R231/R218 (collapse high side)
- R214-R217 (phi_abs cliff)
