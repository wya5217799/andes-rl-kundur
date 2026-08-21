# R420 verdict — 目标修复轮：差模动作惩罚未翻判负，端点回退

**Date**: 2026-08-17
**Status**: completed
**Type**: experiment
**Wall**: ~10h (训练 9 组 + 串行评估/分类)

## TL;DR

R420 added a weight-1.0 action-effort penalty to the CD differential channel on the R419 slew-state bundle: the canary remains CANARY-FAIL, the message arm's endpoint ratios regress from 0.6954/0.7104 to 2.3641/1.9440 and its message increment over the no-message arm flips to -35.25%/-34.02%, the no-harm guard profile worsens (common-frequency 19->36, worst-peak 28->34), and the unchanged scalar arm pins the effect to the single registered factor.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R420.md`

## 给 PI 的话

**发生了什么**：接着上一轮的实测结论，我在已经修好的学习组上，给训练目标补了一条"动作幅度要小"的惩罚，重新训练九个固定预算的学习组；整个过程没有中断，数据全部完整有效。

**这说明什么**：这次补丁没有起到预期作用，反而帮了倒忙。带通信的那组在两个核心指标上从"优于手工参照"退回到"大约是参照的两倍"，通信带来的好处第一次变成负数，比不带通信的那组还差大约三成半；"整体频率不伤害"这条护栏的违反处数从十九处涨到全部三十六处。而没被改动的对照组结果和上一轮一模一样，证明变化确实只来自这一处。所以问题不在"缺一条动作惩罚"，而在目标里"整体不伤害"这条通道没有被照顾到。

**下一步做什么**：下一轮把力气放在"整体不伤害"这条通道上，在上一轮没有加惩罚的基座上给目标补上不伤害条款，仍然只改这一处、同样的预算和种子，看能不能第一次通过全部物理护栏；如果还是失败，就用诊断插桩逐条对比训练过程，找出机制。
