# R422 verdict — 共模通道修复：约束压力撞顶，判负未翻，残余定位到学习动力学

**Date**: 2026-08-17
**Status**: completed
**Type**: experiment
**Wall**: ~3h（训练 9 组 145 分钟 + 串行评估/分类）

## TL;DR

R422 moved the frozen weight-1.0 action-effort term from the CD differential channel (R420 negative) to the CD common channel: the canary remains CANARY-FAIL with no guard count improving (worst-peak 34->36, RoCoF 21->26), the common-channel Lagrange multiplier saturates at its ceiling (last-20 median 10.0 in 6/6 runs versus ~0 in R419/R420), the message arm stays at 2.3999/1.6625 of the deterministic reference with a +21.16%/+7.56% message increment, and the scalar arm is unchanged — so together with the R421 readout the residual failure localizes to the learning dynamics rather than a missing reward term.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R422.md`

## 给 PI 的话

**发生了什么**：我把"动作幅度要小"这条惩罚从上轮的通道搬到了"整体不伤害"通道，重新训练九个固定预算的学习组，与前一轮并行跑完，全部数据完整有效。

**这说明什么**：判负仍然没有翻。更糟的是，"整体不伤害"的约束压力从之前的几乎为零，直接撞到上限并全程拉满——说明这条惩罚加得太重，把整条通道压死了，护栏一条都没改善，还有两条反而更差；带通信那组仍只有最强手工参照的一半不到，通信带来的好处虽然回正，但绝对水平远不如最好那次。把三轮结果和诊断轮的训练曲线合起来看，结论清楚了：问题不在"缺哪一条惩罚"，而在学习过程本身的估价部分持续走坏——对训练目标继续修修补补到头了，下一步要转向修学习过程。

**下一步做什么**：下一轮把唯一改动放到"估价稳定性"上，先按文献确认这类问题的标准修法，再定协议、照常走预注册流程；同时在空闲算力上推进五种子扩展和精确复现这两项排队任务。
