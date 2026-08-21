# R421 verdict — B3 诊断插桩重跑：字节一致锚 + 估价发散 + 共模约束从未激活

**Date**: 2026-08-17
**Status**: completed
**Type**: experiment
**Wall**: ~2.5h（训练 6 组 141 分钟，含 R422 共享负载）

## TL;DR

R421 (B3) reran the R410-bundle arms with bit-non-perturbing diagnostics: the anchor is R410-BIT-IDENTICAL (6/6 byte-identical checkpoints, 43,200 steps each), and the frozen P3 readout shows optimization-failure signals in 6/6 runs (critic loss Q4/Q1 24.4-126.4x, TD-error std 4.9-11.3x), policy stagnation in 5/6, value-estimation signals in 4/6, a never-binding common-channel Lagrange multiplier (median 0.0 in five runs), and no exploration collapse.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R421.md`

## 给 PI 的话

**发生了什么**：我给训练过程装了一套只读的记录仪表，完整记下两个通信配置、各三个随机起点共六组的训练全过程；六组重跑的最终模型与历史存档逐字节一致，证明记录本身没有干扰训练。

**这说明什么**：曲线显示训练后期估价部分持续走坏，损失涨到几十倍、最高一百多倍，而动作部分的更新信号衰减到几乎消失——学到后面动作基本不再朝正确方向调整，这正好解释了为什么最终策略仍高频抖动、反复违反物理限制。另一个关键发现：训练目标里那条"整体不伤害"的约束从头到尾一次都没有被激活过，压力指标几乎恒为零，等于这条安全约束形同虚设。边界要说清：这六组测的是旧基座，最好的新基座正在并行验证，结论迁移过去之前还不能下定论。

**下一步做什么**：正在并行的新一轮实验把"动作幅度要小"的惩罚搬到了"整体不伤害"这条通道上，按本轮读数这可能恰好激活那条从未生效的安全约束。等它出结果，两轮证据合起来决定继续修目标还是转去修估价部分。
