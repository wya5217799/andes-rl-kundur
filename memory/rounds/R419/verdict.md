# R419 verdict — B1 限速状态修复包：端点翻转，判负未翻转

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~6h (含 R418 abort 与第 9 分片重启)

## TL;DR

R419 (B1) repaired the slew-state contract: the CD arms' endpoint ratios
flip from 2.95-5.26x to 0.70-1.23x of the deterministic reference with a
clean positive message increment (+43.45% / +25.59%), the ablation proves
the policies use the added feature, and the canary remains CANARY-FAIL
with every block still violating the action-stress guards, localizing the
residual failure to the objective-to-gate gap.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R419.md`

## 给 PI 的话

**发生了什么**：按文献确认的方案，我把"上一拍实际执行的动作"补进学习
输入、并让目标计算与实际执行同一套语义，重新训练了九个固定预算的学习
组（中途一次程序缺陷按纪律作废重跑、一次文件字节漂移按纪律恢复后重跑
单个分组）。全部数据完整有效。

**这说明什么**：这轮把"为什么学不好"的头号嫌疑从假设变成了实测结
果——修好后，带通信的那组在两个核心指标上第一次**优于**最强手工参照
（分别是参照的约七成），通信增益第一次转正（两个指标分别提升约四成和
四分之一），把新补的特征挡掉后重新评估，证明这些策略真的在用新补的特
征。但判负本身没有翻：每一组仍然全部违反动作强度限制、部分伤害整体频
率。所以剩下的失败原因被钉在"训练目标里没有动作强度与无伤害条款"这一
点上——机制链条第一次这么清楚。

**下一步做什么**：按这条实测机制走下一轮——在已修复的基座上给训练目
标补上动作强度惩罚（单因素、同预算、同种子），看能否第一次通过全部物
理护栏；同时用诊断插桩重跑对比两条基座的完整训练曲线。结果按预注册分
支处理并更新论文。
