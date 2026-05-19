# R170 verdict — hreg λ=0.003 at s54, geo=0.4091 (PROJECT SINGLE-POLICY SOTA)

**Date**: 2026-05-19
**Status**: COMPLETED-POSITIVE (retro by R171 Gap 1 detection)
**Type**: research

## TL;DR

td3_lstm_hreg at s54 with λ=0.003 produced **geo=0.4091** — the
strongest single policy in the project, surpassing R100 (0.383,
λ=0.01) by +6.8% and within 0.003 of R154 4-way ensemble SOTA 0.4119.

Full sweep context in CLM-0325: λ scan {0.003, 0.005, 0.01, 0.03}
peaks at 0.003-0.005, with λ=0.003 (this round) as the peak.

## Questions opened (this round)

(none — but creates a new R172 candidate experiment for R170-in-
ensemble swap)

## Questions closed (this round)

(none — single-policy near-ceiling but doesn't break R154 ensemble)

## Questions advanced (this round, status unchanged)

- Q-0014 — strong near-positive datapoint: single-algo CAN approach
  ensemble SOTA with right hyper (λ=0.003); strengthens the partial-
  positive answer

## 给 PI 的话

🎯 R170 = **项目历史最强 single policy = geo 0.4091**, hreg λ=0.003
at s54。比 R100 (CLM-0190 λ=0.01, geo 0.383) 提升 +6.8%, 距 R154
4-way ensemble SOTA 0.4119 只差 0.003。

这个 finding 差点被 R166 sweep 当 zombie 丢掉 — parallel session 跑了
但没写 claim/verdict。R171 Gap 1 (results-orphan detection) 设计目标
就是抓这种情况, 第一次实战就救回 near-SOTA finding。

**对 paper 的影响**: Sec.IV-D HAWE 故事原本是 "单算法卡 0.391, 集成
跳 0.4119"。现在多一行: 单算法在 λ=0.003 已经 0.4091, 集成只多 +0.7%。
**这削弱"ensemble necessary"的强 claim, 但增强"hreg λ scan critical
in deciding single-policy ceiling"的次 claim**。可能需要重新组织 Sec.IV-D
narrative。

**R172 candidate**: 把 R170 (λ=0.003) plug into ensemble 替 R100
(λ=0.01); 如果模式保持, ensemble 可能 push 到 0.413-0.416 区间, 真
break BREAK gate 0.42 的 first claim 也许就在这里。

(Retro-written by R171 sweep 2026-05-19; near-SOTA finding rescued
from orphan state.)
