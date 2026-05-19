# R216 verdict — phi_abs=2 still COLLAPSE; threshold lies in (2, 10]

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for phi_abs=2; threshold narrows
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with --phi-abs 2.
Result: geo=**0.0100**, LS1=**0.000**, LS2=**0.000**, cum_rf=-0.1816.
**Bit-identical to R214 (phi_abs=0)**: total collapse.

## phi_abs threshold sweep so far

| phi_abs | run | geo | LS1 | LS2 | regime |
|---------|-----|-----|-----|-----|--------|
| 0 | R214 | 0.0100 | 0 | 0 | COLLAPSE |
| **2** | **R216** | **0.0100** | **0** | **0** | **STILL COLLAPSE** |
| 10 | R215 | 0.4061 | 0.353 | 0.467 | near-SOTA (-2.2%) |
| 50 | R201 | 0.4152 | 0.368 | 0.469 | SOTA |

**Sharp threshold somewhere in (2, 10]**: binary-like transition
between full collapse (LS1=0) and near-SOTA (LS1≈0.35).

R217 candidate = phi_abs=5 narrows the bracket further.

## Mechanism interpretation

phi_abs is the "Kundur tight-coupling penalty" — it adds a reward
proportional to |Δω| × |neighbor disturbance|. At small magnitudes
(≤2), this signal is dwarfed by the dominant phi_h/phi_d (frequency
deviation) and gets washed out. The actor cannot use it to find an
LS1-active policy. At ≥10, the signal is large enough to provide a
clear gradient toward "actively manage neighbor disturbances".

The threshold is therefore a **signal-to-noise ratio** issue: phi_abs
needs to be ~5-10× larger than the other reward components' typical
gradient noise to provide a useful learning signal.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

R216 = phi_abs=2 = **0.0100 仍 collapse** (bit-identical R214). Threshold
在 **(2, 10]** 范围内. Binary-like 转换:
- ≤2: full collapse
- ≥10: near-SOTA

R217 = phi_abs=5 narrow 范围. 如果 5 works, threshold (2, 5]; 如果 5
collapses, (5, 10].

机制猜想: phi_abs signal 在小 magnitude 被 phi_h/phi_d 噪声 wash out;
需要 ~5-10× SNR threshold to provide useful gradient. 这是 reward-
shaping engineering 的 quantitative finding.

## Cross-references

- R214 (phi_abs=0 collapse)
- R215 (phi_abs=10 near-SOTA)
- R201 (phi_abs=50 SOTA)
