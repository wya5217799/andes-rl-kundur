# R168 verdict — SAC CTDE eval after loader fix, geo=0.0100 COLLAPSE

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE (R161 SAC CTDE not ensemble-eligible)
**Type**: research (engineering + eval)

## TL;DR

R168 added `SACAgentCTDE` support to `checkpoint_loader.py` (4 ckpts now
load correctly) and used the fix to evaluate R161's SAC CTDE training at
s54: geo=0.0100 COLLAPSE (LS1=LS2=0, cum_rf=-0.197). R161 confirmed
NOT ensemble-eligible. Engineering fix permanent (enables paper-section
CTDE comparison). Full record in CLM-0320.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — adds another negative datapoint to Q-0014's "single-algo
cannot break plateau" closed-partial finding)

## Questions advanced (this round, status unchanged)

- Q-0014 (algorithm-side breakthrough) — SAC CTDE = 92nd negative

## 给 PI 的话

R168 = SAC CTDE 训了但 collapse (geo=0.0100). 这是第 92 个单算法
plateau negative datapoint. 引擎侧顺手修了 checkpoint_loader 让 CTDE
ckpt 可以正确 load — 这个 fix 是永久 infra 改进, paper Sec.IV 可以加
CTDE baseline 比较了, 但 R161 specific 没救活。

R171 sweep 一开始误把 R168 标 aborted reserved-empty (因为 plan.md
不存在), Gap 1 detection 没抓到 (因为 CLM-0320 已经把 round=R168
写出来了, orphan rule skip)。R171 sweep 后期发现 CLM-0320 引用 R168,
手动 retro-stub plan.md + verdict.md 修正分类。

(Retro-written by R171 sweep 2026-05-19 to fix initial misclassification.)
