# R402 verdict — Gate A canary failed, learner route stopped

**Date**: 2026-08-15
**Status**: completed
**Type**: experiment

## TL;DR

The sealed Gate A three-seed canary returns CANARY-FAIL: all 36
arm-seed-profile learning blocks violate the registered no-harm and
action-stress budgets and every arm degrades both registered decoupling
endpoints versus the strong deterministic reference, with no message
increment. The selected learner route stops without algorithm replacement.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R402.md`

## 给 PI 的话

**发生了什么**：按照事先封存的契约，完成了三种学习配置各三个随机起点的
小规模训练，并在全新的考核场景上完成了全部评估。结果很明确：所有学习出来
的控制策略在两个关键物理指标上都比强常规办法差三到五倍，同时动作幅度和
变化剧烈程度超出允许上限好几倍；带设备间消息的完整方法并不比没有消息的
对照更好，反而略差。

**这说明什么**：这次失败不是数据或计算出问题，而是这套学习目标在当前系统
设定下确实学不到比常规办法更好的配合效果，还让设备之间的相互干扰变得更
大，而且付出了更大的控制代价。按照事先约定，这个改进方法到此停止，不再
换算法补救；论文标题里的核心说法依然没有得到支持。

**下一步做什么**：停止这条训练路线，不再投入新的训练。下一阶段的决策交给
论文方向本身：是放弃这个标题、改写为一个纯负结果的技术报告，还是换一个
更小、更容易验证的贡献点，需要明确决定后再动，不再增加实验。
