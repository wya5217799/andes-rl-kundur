# R464 verdict — 限定的十抽头线性类取得正对偶不可行证书

**Date**: 2026-08-21  
**Status**: completed  
**Type**: experiment  
**Wall**: ~0.1h

## TL;DR

有效分类为 `INFEASIBLE-QY10-WITH-VERIFIED-DUAL-BOUND`。在 Object B 的 30 步局部线性锥规划中，QY10 的最优最坏松弛为正，且导出的原始/对偶残差、锥成员关系、间隙、lift 与 DCF 检查共同支持有界数值不可行结论；该结论不外推到更大控制器类或非线性对象。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; R464 uses a named controller class and orthonormal disturbance basis, not the shared-action information-class construction over exact observation histories.

Feed: `paper/yang_md_decoupling_marl/reports/R464.md`

## 给 PI 的话

**发生了什么**：我们把一类边界写得非常清楚的线性控制方案全部放进同一个可核验的数学问题里，并把模型简化、公式展开、求解结果和反向校验所需的数据都完整保存下来。结果显示，即使把这类方案调到允许范围的边缘，也仍然不能同时满足全部要求。

**这说明什么**：这次得到的不是一次搜索没有找到答案，而是针对这类限定方案的数值反证；最主要的矛盾仍在不同方向的扰动相互影响上，而不是动作过大。不过它只覆盖当前模型、时间范围和方案边界，不能据此说所有控制办法都不可能成功。

**下一步做什么**：继续完成误差、灵敏度、稳定余量和统计检验的数据包，再把最后的训练对比单独封存执行。若后续要扩大控制方案范围，会另开新验证，保留这次结论不动。
