# R406 verdict — alpha line-sweep closes the first-order family within the grid

**Date**: 2026-08-16
**Status**: completed — SWEEP-NO-CANDIDATE
**Type**: experiment
**Wall**: ~1.5 h formal execution (one registered pre-repair amendment preserved)

## TL;DR

R406 validly completes all eight frozen alpha grid points on the development
bank; the differential ratio passes at high alpha but the probe-cross ratio
stays at 1.31-1.37 against a 1.10 ceiling for every point. No grid point
passes both frozen thresholds, so the first-order family closes within the
grid and the external interpolation prediction is refuted.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R406.md`

## 给 PI 的话

**发生了什么**：我们按外部方案的建议，把一阶滤波器的角频率在八个预先定好的取值上逐一扫描，每个取值都在同一套六十条仿真轨迹上正式检验。结果很有规律：角频率调高时，机器间摆动能压到达标线以下；但与此同时，另一个关键指标——探测交叉响应——全程比允许上限高出两三成，一个达标的点都没有。

**这说明什么**：一阶滤波这条路被正式关掉了。它的两个目标天然对着干：一个改善另一个就恶化，整个扫描范围内找不到两全其美的点。外部方案"中间某个取值可行"的猜测被实验否定。这不是参数没找对，而是这种一阶结构的固有取舍。

**下一步做什么**：按既定计划进入带通阻尼实验。它在现成的功率通道上运行，专门针对零点四赫兹的振荡频率，并且结构上保证不影响公共频率。控制程序和实验工具都已实现并通过测试，接下来正式走完启动检查再执行。

## 技术路径

- 下一动作: B 轮(带通阻尼)在老线能量端口, 单独领号, 执行器已实现+测试。
- 归档: results/research_loop/r406_alpha_sweep/ (LOCAL-ONLY), 预修补 attempt 保留。
