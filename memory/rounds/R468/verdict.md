# R468 verdict — 物理参数张量有效，归一化策略的光滑展开不适用

**Date**: 2026-08-21
**Status**: completed
**Type**: experiment
**Wall**: ~0.01h

## TL;DR

完整物理 M/D 张量和 30 步 lifted maps 通过收敛与交叉核验；既有有限幅值轨迹支持二次领先，但实现的归一化策略在零点不可微，因此光滑 Taylor 命题不适用。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; local authority tensors do not solve the non-anticipative information-class program.

Feed: `paper/yang_md_decoupling_marl/reports/R468.md`

## 给 PI 的话

**发生了什么**：我们补齐了每台设备参数变化对系统局部动态的完整影响表，并构造了固定观察窗口内的两类作用通道。为了避免浪费，之前已经完成的幅值实验没有重复运行，而是按原始校验值重新分析。

**这说明什么**：物理参数层面的局部关系稳定可靠，已有真实仿真也一致显示其影响以二次趋势为主；另一种直接注入功率的方式则保留明显的一次作用。不过实际控制规则在平衡点两侧不光滑，所以不能把结果写成一个无条件的光滑数学定理，而且平衡误差也没有达到外部清单建议的更严门槛。

**下一步做什么**：继续完成不同通道之间的分离上界检查；随后执行最后一组成本最高的训练对比，并把全部原始数据、校验值、未通过项和失败记录统一打包。
