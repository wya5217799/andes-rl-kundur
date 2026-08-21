# R410 verdict — message-contrast repair: CANARY-FAIL, clean negative increment

**Date**: 2026-08-16
**Status**: completed
**Type**: experiment

## TL;DR

R410 re-executed the R402 canary under the repaired information contract
(no-message arm masks neighbour slots in every actor path) and still
returns CANARY-FAIL, while the message arm now shows a cleanly measured
negative three-seed-median increment over the matched no-message arm
(-78.43% off-diagonal, -26.74% disturbance differential); the R402 drift
anchors are attributed to the R402-registered pre-repair slew projector
with a bit-identical deterministic reference.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R410.md`

## 给 PI 的话

**发生了什么**：把上次学习实验中"不发消息的对照组其实偷偷用了邻居信息"的
设计漏洞修好了，让不发消息的控制程序在训练时也真正看不到邻居。然后按原契约
把三种方案各三个随机起点全部重新训练、重新考核了一遍。结果：所有学习策略
依然全部违反物理安全上限；而且这次在干净的信息条件下，带消息的方案比不发
消息的对照在两个关键指标上分别相差约七成八和两成七——消息不仅没帮忙，反而
明确拖了后腿。另外，两组与上次相同路径的对照数值存在少量出入，
查明原因是上次训练用的一个内部数值修复版本不同，考核环境的基准数据完全
一致，说明偏差只来自训练路径，不是环境变了。

**这说明什么**：论文里那个"消息对比不可信"的明显漏洞已经用实测数据补上了，
而且补出来的结论对论文更有利——不是"没法下结论"，而是"干净地测出来消息
在这个方案组合里是负贡献"。同时，学习方案全部不合格的总体结论没有变，论文
的主叙事不需要任何让步。这次还顺带把上次数值修复遗留的版本混用问题在数据
里说清楚了。

**下一步做什么**：把论文里那几段"只能算描述性对比"的措辞改成实测结论，换
上这一轮的全新数字表，然后按投稿时间表继续收尾。实验部分到此真正结束，不
再追加任何训练。
