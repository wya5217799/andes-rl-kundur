# R465 verdict — 完整总灵敏度通过，A-only 归因不足

**Date**: 2026-08-21  
**Status**: completed  
**Type**: experiment  
**Wall**: ~0.1h

## TL;DR

有效分类为 `TOTAL-SENSITIVITY-VALID`。Object B 的共同 log-M/log-D 完整局部导数通过模式、平衡、规范、Richardson、ZOH Fréchet、全环路、频带与有限窗口复核；R449 的 A-only 近似分别遗漏完整值的 24.24% 和 21.39%，因此不能承担完整因果归因。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; local physical-parameter sensitivity does not solve the non-anticipative information-class program.

Feed: `paper/yang_md_decoupling_marl/reports/R465.md`

## 给 PI 的话

**发生了什么**：我们把惯量和阻尼分别向上、向下扰动，并在每个点重新求解模型，完整计算了从平衡状态、输入输出到控制器和参考方案的全部变化。不同计算方法相互核对后都通过，旧分析中只看状态矩阵的做法确实漏掉了一部分影响。

**这说明什么**：现在可以可靠地说明，在当前模型和平衡点附近，惯量和阻尼变化会怎样改变候选方案相对参考方案的表现。旧近似分别漏掉了约四分之一和约五分之一的完整变化，因此不能再把单个矩阵通道说成唯一原因；这个结论仍然只适用于局部和当前工作状态。

**下一步做什么**：继续计算通信延迟下的全部特征变化，再检查小扰动的二阶效应和不同方向之间相互影响的上界。所有后续结果继续单独封存，最后才进行高成本训练对比。
