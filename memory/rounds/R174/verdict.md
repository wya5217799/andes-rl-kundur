# R174 verdict — td3_lstm_hreg λ=0.002 at s54, geo=0.4139 NEW SINGLE-POLICY SOTA

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (new single-policy SOTA, beats R170 and matches R154 ensemble)
**Type**: research (retro by R176 GC hotfix)

## TL;DR

R174 trained `td3_lstm_hreg` at s54 with λ_h=0.002 (smaller than R170's
λ=0.003 sweet spot). Result: **geo=0.4139** (LS1=0.367, LS2=0.467),
**new project single-policy SOTA**:
- Beats R170 (λ=0.003) 0.4091 by +1.2%
- Beats R154 4-way ensemble 0.4119 by +0.5%

Hreg dose-response sweet spot is tighter than R170 found. λ scan
{0.001, 0.0015, 0.0025} may reveal a true peak.

## Note on GC mishap (R176 hotfix)

Parallel session reserved R174, ran training + eval (results in
`results/r174_w1_hreg_lambda0p002_s54/`), but did not write
`memory/rounds/R174/plan.md`. R176's initial `reserve_round.py --gc`
wrongly classified this as reserved-empty and swept it to aborted.

Hotfix added to `gc_empty_rounds()`: also check for matching
`results/rNNN_*/final_eval_summary.json` before sweeping. Test
case `test_gc_skips_round_with_external_results` covers this
regression.

## Questions opened (this round)

(none directly — but R174 strengthens existing R170 hreg dose-response
finding, paper-relevant)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none formally — but R170 dose-response finding extends; CLM-0325
narrative may need supplement)

## 给 PI 的话

🎯 R174 = hreg λ=0.002 at s54, geo=**0.4139** — **新 single-policy
SOTA**, 超 R170 (0.4091) +1.2%, 超 R154 4-way ensemble (0.4119) +0.5%。
hreg dose-response 比 R170 找到的 λ=0.003 还能再低。

**对 paper Sec.IV-D 影响**: R171 时已经发现 single policy 可以接近
ensemble。R174 进一步证实 single ≈ ensemble (实际超过 +0.5%)。"Ensemble
necessary" 的 claim 进一步削弱。

**GC bug 教训**: R174 差点被 R176 sweep 当 zombie 丢掉 (parallel session
跑了没写 plan.md), 反复出现的 Gap 1 模式。GC 已 hotfix。**这种"跑了
没记"的 race condition 已经是 ledger 第三次出来咬人** (R156/R157
R170 R174), 说明并行 session 写 results 不写 plan 的工作流是系统性的。
Gap 1 (R-results-orphan) + GC hotfix 共同把入侵口堵住, 但根本要靠并行
session 改写 workflow 在 reserve_round.py 之后立刻 write plan stub。

R174 retro verdict 由 R176 sweep 补。看 `results/r174_w1_hreg_lambda0p002_s54/`
拿 numerical evidence。

## Cross-references

- CLM-0325 (R171 hreg dose-response narrative — R174 extends downward)
- CLM-0190 (R100 original hreg λ=0.01 drift-killed)
- CLM-0295 (R154 4-way ensemble 0.4119)
- R170/verdict.md (predecessor sweet-spot)

*(Retro verdict written by R176 GC hotfix 2026-05-19.)*
