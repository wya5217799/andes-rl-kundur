# R300 verdict -- held-out fixed doubled-gain pass

**Date**: 2026-08-03
**Status**: VALID-2KV-PASS
**Type**: experiment
**Claim**: CLM-0710
**Question**: Q-0057 -> closed-positive

## TL;DR

R300 validates fixed `2Kv` over fresh `Kv` on the prospectively sealed bank;
its named executed formulation also exceeds centralized vector PI on both
differential endpoints.

## Questions opened (this round)

- Q-0057 -- held-out evaluation of the R299 fixed retune.

## Questions closed (this round)

- Q-0057 -> closed-positive by CLM-0710.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：没有继续调参，也没有训练网络，直接使用 R299 看结果前封存的 12 个新工况。每个工况重新跑原 `Kv`、固定 `2Kv` 和集中式向量 PI，共 36 条，最后统一做配对区间和全部物理守卫。

**结果（一句话）**：相对原 `Kv`，固定 `2Kv` 的快速区间 IAE 比值为 0.982 [0.972,0.989]、同步损失为 0.970 [0.959,0.976]；相对集中式 PI 则为 0.976 [0.955,0.991] 和 0.910 [0.887,0.926]，36/36 有效且全部公共、储能、动作和零和守卫通过。

**意外**：一个更充分的固定经典增益再次稳定超过了需要更复杂信息路径的集中式 PI；这强化的是当前具体分布式控制律，而不是“多智能体架构天然更强”。

**我默认下一步做**：把 CLM-0710 设为新的最强经典分布式基线。下一轮先从数学模型求相对 RoCoF 增益的耗散/稳定裕度与合理上界，避免继续用 3Kv、4Kv 盲扫；只有模型显示尚有安全余量，才做一个小型增益充分性探针，并仍需独立 eval。

**你想插一脚就说**：若目标是先写会议论文，目前已有一个有正式区间和物理守卫的分布式经典正结果；若标题必须保留 MARL，则还没有证据，必须重新定义一个固定增益无法解决的真实信息或资源异质性问题。

Feed: `results/r300_fixed_2kv_formal/FEED.md`
