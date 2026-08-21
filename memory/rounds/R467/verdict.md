# R467 verdict — 2 s 网格内无名义局部极点越界，性能阈值收紧至 25 ms

**Date**: 2026-08-21  
**Status**: completed  
**Type**: experiment  
**Wall**: ~0.1h

## TL;DR

极点分类为 `NO-CROSSING-UP-TO-2S`，非线性分类为 `FINITE-BANK-FRACTIONAL-BRACKET`。201 个精确分数延迟点的全部 149 个极点均在单位圆内；另外 90 条真实 ANDES 分段输运轨迹把有限场景的 `r_d=0.95` 阈值夹在 0--0.025 s。前者不是鲁棒延迟裕度，后者也不是稳定性边界。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; delay evidence does not solve the non-anticipative information-class program.

Feed: `paper/yang_md_decoupling_marl/reports/R467.md`

## 给 PI 的话

**发生了什么**：我们系统检查了从无延迟到长延迟时的全部局部动态，并在真实仿真里把每个控制周期拆成“旧命令保持”和“新命令生效”两段。第一次运行在保存原始数据时发现结构互相引用，已按规则保留失败记录，并在继任轮次只修复保存结构后完成全部实验。

**这说明什么**：当前名义局部模型在所检查的延迟范围内仍没有越过稳定边界；但有限场景的性能要求对很短延迟就很敏感。这两个结果并不矛盾：系统可以保持局部稳定，同时性能已经不再达标。它们不能合并成一个所谓的鲁棒延迟裕度。

**下一步做什么**：继续检查二阶局部效应和不同部分之间的分离上界，保持每类证据独立封存；最后再执行成本最高的训练对比，并把全部原始数据、失败链和校验清单一起打包交付。
