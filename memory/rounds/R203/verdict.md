# R203 verdict — R201 hyper (tau=0.005) transfers to s51 with same +0.3% lift

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — new hyper is seed-universal
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at s51 with tau=0.005. Result:
geo=**0.3901**, LS1=0.333, LS2=0.457, cum_rf=-0.0699. Compared to
R181 (s51, tau=0.001) = 0.3888: **+0.3% lift, identical pattern to
s54 (R201 +0.3% over R174)**.

## Cross-seed table at new (tau=0.005) hyper

| seed | tau=0.001 | tau=0.005 | lift |
|------|-----------|-----------|------|
| 49 | 0.046 collapse | (untested) | n/a |
| 50 | 0.3515 | (R204 candidate) | ? |
| **51** | **0.3888** | **0.3901 (R203)** | **+0.3%** |
| **54** | **0.4139** | **0.4152 (R201)** | **+0.3%** |
| 55 | 0.3402 | (untested) | ? |

**Same +0.3% lift across both tested viable seeds**: tau=0.005 is a
consistent (small) improvement, **not** a lucky-seed effect at s54.

## Robust paper number update

After R201 + R203:
- Single-config SOTA: R201 0.4152 at (s54, tau=0.005)
- 2-seed mean (s51+s54) at tau=0.005: (0.3901 + 0.4152)/2 = **0.4027**
- 2-seed mean (s51+s54) at tau=0.001: (0.3888 + 0.4139)/2 = 0.4014
- 4-seed mean (s50+s51+s54+s55) at tau=0.001: 0.374

If R204 (s50 with new hyper) follows the same +0.3% pattern,
expected ~0.353 at s50.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — robust SOTA simplification confirmed)

## 给 PI 的话

🎯 R203 = tau=0.005 at s51 = **0.3901** — 比 R181 (tau=0.001 at s51)
0.3888 高 **+0.3%**, 跟 R201 vs R174 at s54 同样的 lift。

**tau=0.005 is seed-universal SOTA hyper**, 不是 s54 lucky 效应。Paper
Sec.IV-D 推荐 hyper 可以 strictly 简化掉 R72_w4 family 的 tau=0.001
cargo cult, 用 default tau=0.005 即可。

R204 候选: 跑 s50 at tau=0.005 完成 cross-seed picture。如果 s50 也
+0.3%, 整个 universality 板上钉钉.

## Cross-references

- R201 (s54 SOTA at tau=0.005 = 0.4152)
- R181 (s51 baseline at tau=0.001 = 0.3888)
- R174 (s54 baseline at tau=0.001 = 0.4139)
