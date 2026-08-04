---
round: R328
---
# R328 verdict - retained controller failure localizes to state estimation

**Date**: 2026-08-04
**Status**: completed - ESTIMATION-LAYER-CAUSE
**Type**: sealed retained-arm model-only information intervention

## TL;DR

R328 closes Q-0081 positive: exact retained augmented state rescues every
frozen development gate while the otherwise unchanged delayed-output observer
controller fails severely, identifying the estimation layer as the causal
blocker for this fixed retained reduced-model controller. The intervention is
an oracle diagnostic, not deployable performance, and Q-0082 opens for one
implementable estimator repair with the remaining controller contract frozen.

## Questions opened (this round)

- Q-0082 - test whether one fixed implementable estimator using only permitted
  signals and history can recover enough of the retained exact-state headroom
  before any holdout, physical, distributed-agent, reward, or training work.

## Questions closed (this round)

- Q-0081 - closed positive by CLM-0850 after the single information-only
  intervention rescued all 32 retained development cases under unchanged
  controller, numerical, constraint, and replay gates.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/decoupling_marl_model_first/reports/R328.md`

## 给 PI 的话

**发生了什么**：这次只把控制器对系统内部状态的错误判断换成真实状态，其余计算方法、动作限制和已知情况全部不变。换完后，全部已知情况都明显好于完全不控制；原来的状态判断却会把波动严重放大。

**这说明什么**：这条路线没有结束，主要故障已经缩小到“没有看准系统内部状态”，而不是计算工具、动作限制或控制目标本身。强行切断不同变化之间的联系仍然不是修复方向。不过，直接使用真实状态相当于提前看答案，不能当作实际可用的方法。

**下一步做什么**：只设计一种能从现有测量和过去记录中判断系统内部状态的方法，其余内容和论文题目保持不变。先在已知情况中检验，未见情况、真实仿真、多个控制单元协同和自动学习继续封闭。
