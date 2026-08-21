# R403 verdict — repaired-successor development attempt invalid

**Date**: 2026-08-15
**Status**: aborted — `SCRATCH-INVALID`
**Type**: experiment
**Wall**: <2h

## TL;DR

R403 is SCRATCH-INVALID by CLM-1170: both repaired arms stopped on the first
critic-only update because the runner treated the intentional NaN
actor-loss sentinel as learner divergence. No algorithm efficacy was tested;
only a separately sealed diagnostic correction successor may proceed.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R403.md`

## 给 PI 的话

**发生了什么**：我们先修了共同目标失效和动作过猛的问题。小规模试验刚
进入首个完整学习更新，记录程序就把“这一步还没有产生某项记录”误当成了
坏数值，因此提前终止。复查确认当时已有的计算数值正常，系统也没有失稳。

**这说明什么**：这是执行记录的缺陷，不是改进方法的成败结果。本轮必须
作废，留下的短片段也不能用来说明控制效果，更不能支持论文里的核心说法。

**下一步做什么**：封存现场并关闭本轮，另开一次独立修正，只改记录方式，
同时把开跑前的排练延伸到首次完整学习更新；其余目标、数据范围、运行步数
和判断标准全部保持不变。如果修正后仍出现异常，就立即停止。
