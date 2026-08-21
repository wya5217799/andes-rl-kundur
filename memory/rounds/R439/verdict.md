# R439 verdict — 时变动作 oracle: 发现时变族 headroom

**Date**: 2026-08-19
**Status**: completed
**Type**: experiment
**Wall**: ~3h

## TL;DR

R439 把 RQ2 从静态律族扩展到有界时变族：outcome-seeing 时变增益 oracle
（2-3 段）在全部 4 个评估 profile 上相对静态选中律改善扰动差分端点
9-14% 且交叉响应不劣化，分类 TIMEVARYING-HEADROOM。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R439.md`

## 给 PI 的话

**发生了什么**：为了回答"如果允许控制增益随时间变化，是不是还有改进
空间"这个审稿人可能问的问题，我们做了一个有边界的搜索实验：把每个
场景的时长分成两到五段，每段用不同的增益组合，在四个评估场景上逐一
搜索更好的分段方案。

**这说明什么**：答案是肯定的——四个场景全部找到了比原来的固定增益
方案更好的分段方案，扰动后的机组间振荡能量下降了约一成到一成半，同时
没有伤到另一个指标。这推翻了之前"固定增益已到顶"的结论的适用范围：
固定不变时确实没有余地，但允许分段变化时确实有余地。注意这只是一个
"存在性"证据（事后搜索出来的最好方案），不等于能实时部署的控制律。

**下一步做什么**：这一环收尾归档，把"静态族无余量、时变族有余量"的
边界写进论文讨论部分；继续处理剩余实验环的收尾。
