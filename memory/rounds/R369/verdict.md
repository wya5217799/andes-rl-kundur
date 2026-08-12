# R369 verdict — deterministic positive, learning headroom negative

**Date**: 2026-08-12
**Status**: completed - STOP-NO-CONDITIONAL-HEADROOM
**Type**: analysis
**Wall**: <1h

## TL;DR

R369 validates the immutable development bank and finds strong deterministic
efficacy but insufficient conditional oracle headroom, so CLM-0990 closes
Q-0103 negative and stops direct per-VSG M/D training.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- Q-0103 closed-negative by CLM-0990; the registered direct-M/D formulation
  failed its prospective finite-family pretraining-headroom screen.

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R369.md`

## 给 PI 的话

**发生了什么**：修正数值核验后，固定规则控制把设备之间的差异波动降低了约七成，而且没有触发整体频率或动作约束问题；但按每个场景事后挑选最佳规则，也只能再改善约百分之一，达不到事先要求的百分之五。

**这说明什么**：系统和控制入口并不是完全没有作用，但这套有限检查没有证明固定规则之后还留下了足够的学习空间。动作会随时间变化，也会因场景选择不同规则，因此失败不是动作不变化；它也不能证明所有可能动作都没有空间，只能说明现在没有足够依据投入训练。

**下一步做什么**：停止这套直接调节参数的学习方案，不换算法、不改奖励做搜索。回到方向选择，只考虑真正改变每台设备可协调作用方式的新方案，并先用非学习上界证明留下足够空间，再决定是否训练。
