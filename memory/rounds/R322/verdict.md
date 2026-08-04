# R322 verdict - no single failure mechanism is identified

**Date**: 2026-08-03
**Status**: completed - MECHANISM-NOT-IDENTIFIED
**Type**: development-only causal diagnosis
**Wall**: ~1h

## TL;DR

R322 validly finds mixed arm-dependent gain-authority and estimation effects under its development-only signatures, so it identifies neither one dominant mechanism nor an admissible common scalar repair.

## Questions opened (this round)
- Q-0078 - formulate at most one actuator-constrained finite-horizon deterministic controller from model equations, delay, and physical limits without using the R321 examination or a weight grid.

## Questions closed (this round)
- Q-0077 - closed-negative by CLM-0820.

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R322.md`

## 给 PI 的话

**发生了什么**：我们只用早已公开的练习情况，把“命令过猛”和“判断偏差”拆开检查。假设系统状态完全知道，一种方案的平均结果改善了约三分之二，但仍远远不及格；另一种方案反而变得更差。两种方案的命令都超过设备能执行的程度，同时判断偏差也都很大。

**这说明什么**：上次失败不是一个单独问题造成的，不能简单归结为命令太猛，也不能简单归结为判断不准。事先规定的单一主因条件没有满足，所以我们没有生成缩小后的新方案，也没有启用新的考试。这避免了看见混合结果后，硬挑一个解释继续试。

**下一步做什么**：停止修补这套固定收敛速度的办法。下一步从设计开始就把设备能做多大、能变多快写进去，只在练习情况上形成一个全新的固定方案；如果连练习情况都不能稳定达到要求，就停止这条传统控制路线。论文题目保持不变，暂时仍不做真实仿真，也不让多个控制单元自己学习配合办法。
