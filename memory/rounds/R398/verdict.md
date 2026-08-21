# R398 verdict — Yang-compatible M/D decoupling-MARL successor registration

**Date**: 2026-08-15
**Status**: completed
**Type**: analysis

## TL;DR

R398 registers `yang-md-decoupling-marl` as a separate fixed-title successor and returns `ALLOW` only for its prospective non-learning joint-headroom gate. The future MARL comparison remains `QUALIFY` and launch-blocked until its bank, physical semantics, estimands, uncertainty, capacity, training, tuning, and selection budgets are frozen.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R398.md`

## 给 PI 的话

**发生了什么**：原来的实验路线已经走到停止点，所以这次没有硬接着改算法，而是另建了一条独立路线。新路线保留每台设备各自调节两个关键参数的做法，同时把“减小相互影响”落实为整体变化和设备间差异都要接受检验。本轮只完成路线、比较方法和停止条件，没有运行新仿真，也没有训练。

**这说明什么**：新题目现在有了能够被实验直接检验的含义，也明确了哪些旧代码可以继续用、哪些旧结果不能搬过来。目前达到的是研究设计合格，不是控制效果合格；还不能说设备之间的相互影响已经减小，也不能说多设备学习已经有效。

**下一步做什么**：先在新的多种工况下，用不学习的方法检查强常规控制之后是否还留有足够的共同改善空间。如果空间不足，就立即停止这条路线；只有空间明确存在，才进入全新的多设备训练。
