# R297 verdict -- full-anchor development candidate

**Date**: 2026-08-02
**Status**: RELATIVE-ROCOF-FULL-AMPLITUDE-CANDIDATE-IDENTIFIED
**Type**: experiment
**Claim**: CLM-0695
**Question**: Q-0054 -> closed-positive

## TL;DR

R297's final full-anchor residual passes every development gate and freezes one
candidate for the already-predeclared disjoint held-out evaluation; it is not
yet formal performance evidence.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0054 -> closed-positive by CLM-0695.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：只做了最后一个 100% 目标幅值，没有再加中间点。基准和候选使用完全相同的四个本地 agent、频率历史、邻居消息、动作、约束和工况；8 条轨迹分三路完成。同时在看结果之前就把下一步 12 个新工况写进了 seal。

**结果（一句话）**：残差使快速区间 IAE 改善约 1.99%、同步损失改善约 3.61%，所有公共、储能、动作、完成与零和守卫均通过，因此它成为唯一允许进入完整 eval 的候选。

**意外**：R296 的 50% 幅值确实只是略微不够，而不是结构饱和；增至 100% 后跨过了原门槛，同时公共频率几乎不受损。这个结论仍只来自开发工况，不能写成性能优势。

**我默认下一步做**：立即停止调增益，按已预先冻结的新工况比较原 DAPI、残差 DAPI 和集中式向量 PI，并报告配对区间与全部失败守卫；只有那一轮通过才进入论文证据或神经网络增量比较。

**你想插一脚就说**：完整 eval 的场景、三组控制器和结论上限都已限定；若不希望继续算，可以现在停在“候选已找到但未验证”，否则我按完整 eval 推进。

Feed: `results/r297_relative_rocof_amplitude/FEED.md`
