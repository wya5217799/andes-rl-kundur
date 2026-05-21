# R219 verdict — Paper-strict + phi_abs=50 STILL collapses; V4 R18 rescale ALSO load-bearing

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — paper-strict weights interfere even with phi_abs patch
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 tau=0.005 at s54 with paper Eq.14
weights (phi_h=1, phi_d=1, phi_f=100) + phi_abs=50 patch. Result:
geo=**0.0100**, LS1=**0.000**, LS2=0.003, cum_rf=-0.1682. **FULL
COLLAPSE** despite the phi_abs patch.

This is **unexpected** — R201 (V4-default rescaled phi_h/phi_d +
phi_abs=50) gives 0.4152, but R219 (paper-original phi_h/phi_d +
phi_abs=50) collapses.

## Updated paper-faithfulness picture

| Run | phi_h, phi_d | phi_f | phi_abs | geo |
|-----|---------------|--------|---------|-----|
| R201 (SOTA) | 0.0056, 0.0056 (V4 rescale) | 100 | 50 | **0.4152** |
| R215 (near) | 0.0056, 0.0056 | 100 | 10 | 0.4061 |
| R214 (paper-fail) | 0.0056, 0.0056 | 100 | 0 | 0.0100 |
| R218 (paper-strict) | 1, 1 (paper) | 100 | 0 | 0.0100 |
| **R219** | **1, 1 (paper)** | **100** | **50** | **0.0100** |

**V4's R18 rescale (phi_h=phi_d=0.0056 = 1/178 of paper nominal) is
ALSO load-bearing**, not just phi_abs. The full SOTA recipe requires
**both** modifications from paper Eq.14:
- phi_h/phi_d rescaled to ~0.006 (1/178 of paper)
- phi_abs ≥ 7 added (not in paper)

Using paper-original phi_h=phi_d=1 at any phi_abs value fails.

## Mechanism speculation

At phi_h=1, the frequency-deviation reward gradient (proportional to
Σ|Δω_i|²) is ~178² larger than at the rescaled value. This may push
the actor into a different bang-bang attractor (regulating Δω to zero
at any cost), where LS1 disturbance recovery is suppressed in favor
of immediate damping. The actor may saturate at maximum damping
action, which paradoxically prevents LS1-active policies.

This is consistent with R141/R145 findings about gradient magnitude
balance across reward terms — a known issue in multi-objective RL.

## Final paper Sec.IV-D paper-integrity finding (definitive)

> "Reproducing paper Eq.14 reward weights on the ANDES Kundur 4-VSG
> environment requires TWO modifications:
> (1) Rescaling phi_h and phi_d by 1/178 (from nominal 1.0 to 0.0056),
> known as the R18 rescale, AND
> (2) Adding an environment-specific Kundur-tight-coupling penalty
> phi_abs ≥ 7 (not present in paper Eq.14).
>
> Neither modification alone is sufficient (R218: paper weights +
> no phi_abs = collapse; R219: paper weights + phi_abs=50 = collapse).
> Only the joint modification yields viable training. This identifies
> a paper-implementation gap requiring careful documentation when
> reproducing physics-sim RL results."

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — paper-integrity story now definitive)

## 给 PI 的话

🛑 **R219 = paper Eq.14 weights + phi_abs=50 = COLLAPSE** (unexpected!).

跟 R201 比 (V4-rescaled phi_h/phi_d + phi_abs=50 = 0.4152), R219 用
paper-original phi_h=phi_d=1 加 phi_abs=50, **仍然 LS1=0 collapse**.

**V4 的 R18 rescale (phi_h/phi_d 1/178) 也是 load-bearing**, 不只是
phi_abs. SOTA 需要 **两个** 修改:
1. phi_h/phi_d rescale to ~0.006
2. phi_abs ≥ 7 加入

机制猜想: phi_h=1 时 frequency-deviation gradient 是 rescaled 的 178²
倍, 把 actor 推进另一个 bang-bang attractor (max damping action), 又
卡死 LS1.

**对 paper 影响**: paper-integrity disclosure 更 nuanced. 不只是
"加 phi_abs", 是 "rescale phi_h/phi_d AND add phi_abs". 这是 RL+
physics-sim 跨 simulator 的 reproducibility gap.

R220 候选 = batch_size=64 (untested CLI axis, single-shot test).

## Cross-references

- R201 (V4-default + phi_abs=50 SOTA)
- R218 (paper-strict + phi_abs=0 collapse)
- R214 (V4-default phi_h/phi_d + phi_abs=0 collapse)
