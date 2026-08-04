# R298 verdict -- held-out relative-RoCoF residual pass

**Date**: 2026-08-02
**Status**: VALID-RELATIVE-ROCOF-PASS
**Type**: experiment
**Claim**: CLM-0700
**Question**: Q-0055 -> closed-positive

## TL;DR

R298 validates the explicit neighbour-local zero-sum relative-RoCoF residual
over fresh DAPI on 12 held-out operating conditions; its named executed
formulation also exceeds centralized vector PI on both differential endpoints.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0055 -> closed-positive by CLM-0700.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：停止所有开发调参，直接使用 R297 看结果前就写入 seal 的 12 个新工况。每个工况重新跑原始本地 DAPI、选中的零和相对 RoCoF DAPI 和集中式向量 PI，共 36 条；三路 WSL scratch 并行，最后统一做配对区间和全部物理守卫。

**结果（一句话）**：相对原 DAPI，残差 DAPI 的快速区间 IAE 比值为 0.972 [0.963,0.979]、同步损失为 0.952 [0.929,0.962]；相对集中式向量 PI 则为 0.983 [0.965,0.995] 和 0.918 [0.897,0.927]，36/36 有效且全部公共、储能、动作和零和守卫通过。

**意外**：原 DAPI 相对集中式 PI 仍是“同步更好、快速 IAE 更差”的旧权衡，但加入严格邻居局部的相对 RoCoF 残差后，两个差模端点同时超过集中式 PI，权衡被打破。这是具体执行形式的结果，不是多智能体普遍优越定理。

**我默认下一步做**：把 CLM-0700 作为新的最强经典分布式基线。若继续追神经网络，只先做“剩余误差是否还可由局部/邻居信息预测”的小型信息价值探针；有可学增量才训练，并同时比较匹配的分布式多网络与集中式单网络。

**你想插一脚就说**：若目标是先交会议论文，这个结果已经能支撑一个有边界的“分布式局部控制优于所测集中式 PI 形式”的新方法段，但不能改写成 MARL 胜出。若坚持 MARL 标题，下一阶段还必须证明神经增量超过这条强经典基线。

Feed: `results/r298_relative_rocof_formal/FEED.md`
