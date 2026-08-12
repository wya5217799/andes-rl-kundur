# R370 verdict — successor mechanism direction

**Date**: 2026-08-12
**Status**: completed
**Type**: analysis
**Wall**: ~1h

## TL;DR

R370 selects a VSG-owned, energy-constrained active-power-reference mechanism
as the sole conditional successor, while rejecting direct reuse of the
independent GFL ESD1 object and authorizing no implementation or execution.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R370.md`

## Technical disposition

- `CLM-0995` records `DIRECTION-SELECTED-WITH-OBJECT-REPAIR` as a trust-S
  programme decision.
- The direct per-VSG M/D formulation remains stopped by `CLM-0990`.
- The current ESD1 environment is an implementation donor only; the next gate
  must establish a VSG-owned power port and energy contract.
- Controller implementation, ANDES execution, training, performance, safety,
  generalization, novelty, and publication claims remain unauthorized.

## 给 PI 的话

**发生了什么**：上一种直接调整设备固有参数的方案已经停止。现在只保留一个新方向：让每台设备拥有自己的受能量约束的功率调节入口。现有储能代码里的能量、功率、变化速度和剩余容量限制可以复用，但现有旁挂储能本身不能直接当成设备内部的调节入口。

**这说明什么**：储能方向仍然有价值，而且是当前最有希望保住既定题目的路线；但它的价值主要在约束和控制基础设施，不在旧实验结果。只有先证明功率入口确实属于每台设备、动作与设备一一对应、能量收支真实，后面的多设备学习才不会再次出现研究对象不匹配。

**下一步做什么**：先做最小的对象检查，不训练。检查每台设备的功率入口、单位、方向、响应时序、单台干预和能量守恒；只要发现它仍然只是旁挂装置在发力，就立即停止这条实现。全部通过后，再检查确定性控制是否有效并留下足够改进空间。
