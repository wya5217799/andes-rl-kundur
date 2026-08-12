# R379 verdict — low-corner high-pass stops on probe no-harm ceiling

**Date**: 2026-08-12
**Status**: completed - STOP-DEVELOPMENT-NO-CANDIDATE
**Type**: experiment
**Wall**: <1h

## TL;DR

R379 moves the damping corner below the measured 0.4 Hz mode (alpha 0.90):
identity holds on all 60 development trajectories and the best candidate
reaches 0.914x local differential energy, but every candidate exceeds the
probe cross-response no-harm ceiling (1.15-1.29x local), so no candidate is
selected. Jointly with R376-R378, this evidences the first-order damping
no-differential-benefit boundary.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R379.md`

## 给 PI 的话

**发生了什么**：把阻尼通道的滤波位置移到实测振荡频率之下后，六十条开发轨迹全部干净，最佳方案的机间振荡能量比对照又降了一些。但所有候选方案的交叉影响都超过了事先规定的上限，按规则仍无方案入选。

**这说明什么**：四轮尝试（两种滤波位置、一种无滤波）形成了一个一致结论：这类简单的滤波型阻尼通道无法同时满足"保留振荡、抑制探针"这对要求。这是机制层面的边界，不是参数没调好。

**下一步做什么**：按事先约定停止这一族方案，训练仍不授权。继续下去只能提出真正不同机制的方案（例如更高阶或基于模型的结构）并重新登记契约；否则该线登记负结果并停止协调方向。
