# R469 verdict — 输入输出边界成立，不伪造全状态投影

**Date**: 2026-08-21
**Status**: completed
**Type**: experiment
**Wall**: ~0.03h

## TL;DR

全部注册局部模型的有限窗口映射与逐频边界通过核验；异质性不能单独预测串扰，且缺少可信物理构造时不报告全状态投影结果。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; local separation bounds do not solve the non-anticipative information-class program.

Feed: `paper/yang_md_decoupling_marl/reports/R469.md`

## 给 PI 的话

**发生了什么**：我们在全部既定参数组合上检查了共同输入如何泄漏到设备间差异，并同时核对了固定观察窗口和完整频率范围。由于系统内部状态包含不对称网络部分，我们没有强行给它们贴上并不存在的共同与差异标签。

**这说明什么**：所有可验证的输入输出边界都包住了实际局部响应，但即使设备参数完全相同，网络本身仍会产生串扰；参数差异增大时，变化幅度还会受到系统放大条件影响。因此不能只拿参数离散程度写成普遍规律。

**下一步做什么**：进入最后一组高成本训练对比，先根据最小有意义差异和已有波动估算需要多少独立训练，再按硬件容量分批执行；如果预算只能得到探索性证据，会明确标注而不夸大结论。
