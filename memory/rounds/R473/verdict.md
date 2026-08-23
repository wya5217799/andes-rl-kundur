# R473 verdict — U2 源因子实验完成:决策端真实邻居源效应成立

**Date**: 2026-08-23
**Status**: completed
**Type**: experiment
**Wall**: ~9.3h (formal training/eval/aggregate, 16 workers + 1 launcher)

## TL;DR

补齐 R472 中断遗留的 12 个缺失训练单元并复用 96 个已封存分片后,R473 完成全部评估与汇总:决策端真实邻居源相对外生随机供体占位的主效应通过材料性与多重比较门槛,动作端无显著差异,预注册分类为支持。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; the completed U2 factorial does not certify or refute the information-level margin program.

Feed: `paper/yang_md_decoupling_marl/reports/R473.md`

## 给 PI 的话

**发生了什么**：之前因关机中断的那组对比实验，这次把缺失的训练单元全部补完，已完成的直接复用不再重新训练，随后跑完所有评估和汇总，全程没有发现数据损坏或训练异常。

**这说明什么**：接入真实邻居运行信息的方案，比接入随机替代信号的方案，在从未见过的场景上平均表现好约 19%，差距超过事先约定的最小有意义线，统计上也不是碰巧；但在生成动作的那一侧没有观察到同样效果。按事先约定，这只能说明真实邻居信号整体上有用，不能拆成纯粹由信息内容带来的，更不能推广成任何普适说法。

**下一步做什么**：这是计划中最后一项高成本训练，本轮就此正式关闭。接下来在稿件的下一次统一更新时，把这项结果和它的边界写进对应章节；如果草稿里发现与它冲突的旧表述，会先标出来再处理。
