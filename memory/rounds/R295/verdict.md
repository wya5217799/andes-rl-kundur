# R295 verdict -- DAPI consensus-time-scale no-go

**Date**: 2026-08-02
**Status**: CONSENSUS-TIMESCALE-NO-GO
**Type**: experiment
**Claim**: CLM-0685
**Question**: Q-0052 -> closed-negative

## TL;DR

R295 confirms that faster neighbour consensus suppresses DAPI's internal
differential integral state, but the registered fast inter-area endpoint
changes by less than 0.1%; gain tuning stops and no full performance evaluation
is authorized for these candidates.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0052 -> closed-negative by CLM-0685.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：没有继续蒙神经网络，而是把 R294 暴露的小差距拆成一个最便宜的机制问题：是不是邻居积分一致性太慢。我们固定了四个真实本地 agent、信息、动作、约束和其余增益，只改变一致性速度，三组共跑了 12 条密封轨迹。

**结果（一句话）**：一致性增益从 1 提到 2 和 4 后，内部差模积分 RMS 分别下降 21.45% 和 45.95%，但快速区间 IAE 只改善 0.065% 和 0.070%，没有达到预注册的 1% 门槛，所以该方向判定 NO-GO。

**意外**：数学上目标状态确实被明显压下去了，物理端点却几乎不动；这说明问题不是“积分共识速度不够”，而是该项在最终差模功率动作里太弱。这个负结果排除了继续扫一致性增益，反而把下一步靶点缩小了。

**我默认下一步做**：不为失败候选浪费完整 eval；转向严格邻居局部、边上反对称且总和为零的相对 RoCoF/相位超前残差。先用同样规模的微型机制试验验证它是否真正改变主导差模动作，过门后再开全新工况的完整 eval。

**你想插一脚就说**：如果你希望优先写会议稿，可以停在 R294 的有界经典分布式结论；如果继续追多网络相对单网络的增量价值，就必须先让新的结构残差超过这个 DAPI 强基线，再训练神经网络。

Feed: `results/r295_consensus_timescale_probe/FEED.md`
