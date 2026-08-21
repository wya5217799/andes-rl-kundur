# R423 verdict — 修估价单因素：梯度裁剪压发散但不截断，系列首次无伤害护栏好转，判负未翻

**Date**: 2026-08-17
**Status**: completed
**Type**: experiment
**Wall**: ~3h（训练 9 组 128 分钟 + 串行评估/分类）

## TL;DR

R423 applied the frozen critic gradient clip (max_norm 1.0) to the CD arms on the R422 bundle: the canary remains CANARY-FAIL (36/36 blocks) but yields the family's first no-harm guard gains (RoCoF 26->22, worst-peak 36->35), moves the CD endpoints toward the deterministic reference (message arm 2.3999->1.7756 off-diagonal ratio), damps the critic-loss Q4/Q1 growth to 5.0-8.0 without reaching the 3x stopping threshold, keeps the common multiplier at its 10.0 cap, and leaves the scalar arm byte-identical to R422 (3/3) — the divergence is damped, not stopped, and the invariant 36/36 action-stress failures are consistent with the constraint-hierarchy diagnosis; the modal identities were verified numerically (residuals <= 7e-18) with executed actions 0.36-0.82 differential-dominant.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R423.md`

## 给 PI 的话

**发生了什么**：我给估价网络的更新幅度加了一道固定上限，重新训练九个固定预算的学习组，全部完整有效；对照组的三份最终模型与上一轮逐字节一致，机器验证改动只落在估价部分，没有碰到别的环节。

**这说明什么**：结果没有翻盘——安全红线依然全部不达标。但出现了整个系列里第一次实质好转：整体不伤害的两项指标分别从二十六处降到二十二处、从三十六处降到三十五处，端点到最强手工参照的距离也明显缩短；估价发散的幅度从上轮的几十到一百多倍压到了五到八倍，可没有压到事先约定的三倍以下，说明发散的原因不光是步子太大，根子在目标值本身的水涨船高。更关键的发现是：动作压力类红线从第一轮起就全部失败、四轮纹丝不动，而数学核对证明训练目标里根本没有对应这项红线的内容——所以改估价只能让训练更稳，改善不了"目标里没有的东西"。

**下一步做什么**：下一轮按您指定的优化方向，把动作压力红线直接写进训练目标——给动作幅度和动作变化量各配一个会自动调节大小的权重，其余全部不变，只改这一处；同时把本轮结果和已经写进论文的理论修正补齐，流程继续自动推进。
