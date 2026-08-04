# R304 verdict — topology gate invalid before modal identification

**Date**: 2026-08-03
**Status**: INVALID-TOPOLOGY-GATE
**Type**: experiment
**Claim**: CLM-0730
**Question**: Q-0061 -> open

## TL;DR

R304 did not measure topology-information value because its sealed runner
failed while coercing the multi-element `PFlow.run()` return to a scalar
boolean. The vector-inertia EVAL engineering gate passed separately, but both
the time-domain comparison and neural training remain blocked.

## Questions opened (this round)

- Q-0061 — topology-conditioned zero-sum vector-inertia information value.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0061 — adapter root cause bounded; scientific estimand remains unmeasured.

## 给 PI 的话

**这轮干了啥**：冻结了 nominal、Line_0 断开、Line_9 断开三种配置和七个零和惯量分配，三路并行跑完 21 个小信号单元；同时把真正向量惯量动作需要的 EVAL 请求、命令、实际读回和拓扑检查补齐。

**结果（一句话）**：这轮是 `INVALID-TOPOLOGY-GATE`，21/21 单元都在读取有效模态前被同一个执行器错误截断；EVAL 的 57 个工程测试通过，但不能据此开始时间域比较或训练。

**意外**：问题不在拓扑或算法，而在 ANDES 接口语义：当前版本的 `PFlow.run()` 返回多元素数组，封印脚本却把它直接当布尔值；因此不能把全体 guard 失败误读成三种拓扑都不可行。

**我默认下一步做**：关闭 R304 但保持 Q-0061 开放；新开最小修复轮，改读权威 `PFlow.converged`，先跑 nominal/q0 单单元 canary，全部守卫通过后才并行补齐余下 20 个单元。只有静态价值和 EVAL 同时通过，才允许另开 12-case 经典控制比较；训练仍不开放。

**你想插一脚就说**：如果你要改变三种拓扑或七个动作的科学设计，需要在新轮封印前提出；否则我只修执行适配器，不改动作、阈值、模式带或结论规则。

Feed: `results/r304_topology_vector_gate/FEED.md`
