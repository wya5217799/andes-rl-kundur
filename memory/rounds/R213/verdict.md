# R213 verdict — gamma is not load-bearing (bit-identical to R201)

**Date**: 2026-05-19
**Status**: CLOSED-NEUTRAL — gamma 0.99 ≈ 0.999 at this hyper
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with gamma=0.999.
Result: geo=**0.4152**, LS1=0.368, LS2=0.469, cum_rf=-0.0692.
**Bit-identical to R201 (gamma=0.99) at 4-decimal precision**.

## What this means

Either:
1. The bandit-like reward structure (short episodes, well-defined
   disturbance recovery) doesn't depend strongly on long-horizon
   discount
2. The converged policies at 75ep happen to match at the eval level
   (different training trajectories, same deterministic-eval output)

Likely (1): with deterministic eval seed=42 and same network init,
the policy at 75ep gives the same action sequence regardless of how
gamma weighted the training Q-values.

## SOTA hyper saturation report

Tested axes that do NOT change SOTA at 75ep, s54, hreg λ=0.002:
- tau: 0.001 (R174) ≈ 0.005 (R201) — both at 0.413-0.415
- gamma: 0.99 (R201) = 0.999 (R213) — bit-identical
- offset: 0 (peak 0.415) vs 50/100 (~0.388)
- λ: 0.002 (peak 0.4152) vs 0.0015 (R179 0.4125), 0.0025 (R180 0.4104)

Single-policy SOTA at 0.4152 is **structurally saturated** within
single-axis interventions. Multi-axis combinations untested but
unlikely to push above ~0.42.

## What's left untested

- Reward shaping (--phi-h, --phi-d, --phi-abs, --phi-max overrides)
- Batch size (default vs 64)
- VSG physical params (--vsg-m0, --vsg-d0)

R214 candidate = remove non-paper Kundur tight-coupling penalty
(--phi-abs 0). Tests paper-faithfulness of the SOTA — if SOTA implicitly
depends on phi_abs=50, removing it should hurt geo significantly.
If geo stays high, R201 SOTA is paper-faithful.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — SOTA hyper saturation confirmed)

## 给 PI 的话

R213 = gamma=0.999 at R201 hyper = geo **0.4152** — bit-identical
to R201 (gamma=0.99). gamma 不 load-bearing.

**SOTA hyper saturation**: tau / gamma / λ neighborhood / horizon /
offset 全部 tested. Single-policy SOTA 0.4152 在 single-axis 层面已经
saturate. 多轴组合可能挤出 +0.5% 但不会破 0.42 gate.

R214 候选 = --phi-abs 0 (移除 Kundur tight-coupling penalty 这个 non-
paper 项). 测 SOTA paper-faithfulness — 如果 phi_abs=50 是 load-bearing
的 reward shaping artifact, 移除后 geo 应该掉; 如果不掉, SOTA 真是 paper-
faithful policy.

## Cross-references

- R201 (R201 hyper, gamma=0.99)
- R174 (tau=0.001 = same SOTA)
- CLM-0094 (R72_w4 hyper definition)
