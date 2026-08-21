# R407 verdict — bandpass stage fails the disclosed gate

**Date**: 2026-08-16
**Status**: completed — BAND-FAIL
**Type**: experiment
**Wall**: parallel execution (8 workers, rung-8 ladder); three registered
pre-repair amendments preserved

## TL;DR

R407 validly completes all five frozen K points with every guard passing; the
bandpass improves the probe-cross ratio (0.68 at K=2) but degrades the
disturbance differential ratio at every gain (1.03-1.19 versus 0.95), so no K
passes both frozen thresholds and the stage closes BAND-FAIL. The trade runs
opposite to the closed first-order family.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R407.md`

## 给 PI 的话

**发生了什么**：我们把一个专门针对零点四赫兹振荡的带通阻尼环节放进了机器功率通道，在五个预先定好的强度上逐一正式检验。结果是两个指标依然对着干，但方向反过来了：强度越高，"不同调节方向互相干扰"这个指标越好（最好时只相当于基准的七成），而"受扰后的机器间摆动"这个指标在每个强度上都比基准差百分之三到百分之十九，全部不达标。

**这说明什么**：带通环节的空间设计达到了它自己的目的——它确实压住了干扰方向；但它在摆动指标上帮了倒忙。至此，外部方案建议的三种修改——调成一样、一阶滤波、带通阻尼——在真实物理检验中全部没有通过及格线。这三条路线的证据方向一致：系统的剩余空间不在题目要的方向上。

**下一步做什么**：全部三组实验已经收束，实验侧正式关闭。下一步是把这些有边界的否定证据写进论文：明确写出哪些做法被检验过、各自为什么失败、以及证据能说与不能说的边界。论文按此前确定的骨架推进，标题词保持"未获支持"。

## 技术路径

- 下一动作: manuscript 收束(实验侧关闭; 三路线证据链完整)。
- 归档: results/research_loop/r407_bandpass_gate/ (LOCAL-ONLY), 三个预修补 attempt 保留。
