# R292 verdict — true distributed vector comparison

**Date**: 2026-08-01
**Status**: COMPLETED — `INVALID`
**Type**: experiment
**Claim**: CLM-0675
**Question**: Q-0049

## TL;DR

R292 completed its sealed matrix but is `INVALID` because the prospectively frozen relative no-harm guard failed. Q-0049 closes partial without a valid architecture-performance answer, and all directional estimates stay out of manuscript claims.

## Questions opened (this round)

- None.

## Questions closed (this round)

- Q-0049 — `closed-partial` by CLM-0675 because the exact frozen comparison is `INVALID`.

## Questions advanced (this round, status unchanged)

- None.

## 给 PI 的话

**这周干了啥**：把真正的三维零和边流分布式控制与匹配的集中式向量控制放进同一套冻结训练、同一扰动库和同一物理约束里；电脑重启后只续跑通过哈希核验的缺失轨迹。

**结果（一句话）**：168 条轨迹全部完成，但正式结论是 **INVALID**；五个学习种子臂超过了预先冻结的相对无伤害门，主要是 RoCoF 尾部恶化，因此不能用这轮证明分布式控制有效、优于或不劣于集中式。

**意外**：分布式臂在两个主端点上出现了方向一致的改善信号，但同一批数据没有通过尾部守卫；两个集中式种子也失败，所以这更像需要重新提出的物理问题，不能归因于分布式架构本身。

**我默认下一步停**：不改阈值、不挑种子、不补跑 R292，也不把无效方向性数字写进论文。先把本轮作为负面证据封存，会议稿继续使用已有的受限标量结论和明确局限。

**你想插一脚就说**：如果还要追这个问题，需要另开前瞻轮次，先决定是研究 RoCoF 尾部与零和惯量残差的冲突，还是重新设计比较对象；不能在 R292 上事后修补。

Feed: `results/r292_formal_evaluation_v3/FEED.md`
