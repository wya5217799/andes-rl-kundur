# R449 verdict — P1.1 状态矩阵通道对 M/D 均为混合贡献

**Date**: 2026-08-20
**Status**: completed
**Type**: analysis
**Wall**: ~1h

## TL;DR

R449 修复 R448 的无效 D 扰动后，在冻结的 Object B 小信号模型中测得 M、D 的状态矩阵通道均为 `MIXED`；该结论只覆盖 A-channel，不覆盖未传播的 B/C 灵敏度或非线性因果归因。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R449.md`

## 给 PI 的话

**发生了什么**：上一次有一项改动实际上没有接到生效的位置，我保留了那次失败记录，换到新一轮后把连接修正并重新测量。现在两类参数变化都真正进入了模型，结果也通过了预先设定的检查。

**这说明什么**：候选方案本身和参照方案会朝相反方向拉动结果，而且力量接近，没有任何一边能单独解释之前的失效。这个判断只适用于当前工作点附近的简化分析，不能当成完整的因果结论。

**下一步做什么**：继续检查信号晚到一步或两步时结果怎样变化，并先把信号从哪里断开这件事定义清楚；如果定义不能唯一对应真实控制路径，就停止测量而不强行给结论。
