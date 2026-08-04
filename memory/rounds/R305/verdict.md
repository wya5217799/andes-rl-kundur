# R305 verdict — no static topology-information value

**Date**: 2026-08-03
**Status**: NO-STATIC-TOPOLOGY-VALUE
**Type**: experiment
**Claim**: CLM-0735
**Question**: Q-0061 -> closed-negative

## TL;DR

The repaired, valid 3-by-7 EIG matrix selected `e01_pos` for every tested
configuration, so one fixed allocation matched every topology-conditioned
oracle with zero information headroom. Q-0061 closes negative; the dynamic
comparison and neural training remain blocked.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0061 -> closed-negative by CLM-0735: no static topology-information value
  in the frozen configuration and action set.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：先修正 R304 的 ANDES 收敛状态读取，再用严格 canary 卡住正式仿真；canary 通过后，三路并行跑完 nominal、Line_0 断开、Line_9 断开下的 21 个零和惯量分配，并用新 vector-inertia EVAL 核对执行合同。

**结果（一句话）**：有效结论是 `NO-STATIC-TOPOLOGY-VALUE`——三种配置都选择同一个 `e01_pos`，固定动作与逐拓扑 oracle 的差距为 0%，因此没有理由进入 12-case 拓扑信息比较或训练单网络/多网络智能体。

**意外**：负结果不是“惯量空间分配没用”。`e01_pos` 相对 q0 在三种配置都提高了所识别局部模式的阻尼，最差比值仍为 1.146；真正被否定的是“必须知道拓扑、并据此采用不同动作”的假设。

**我默认下一步做**：停止 Q-0061，不为保住 MARL 标题继续换拓扑或扫网络；把 `e01_pos` 记作未来研究必须击败的固定经典空间基线。研究程序回到 idle，等新的、数学上明确且经典控制不能关闭的机制问题，再决定是否训练。

**你想插一脚就说**：如果你仍希望证明多智能体优势，需要重新定义一个局部信息确实改变最优决策、且强固定/分布式经典基线仍有缺口的问题；不能从这组结果推出 MARL 更优，也不能直接塞回当前会议论文。

Feed: `results/r305_topology_vector_gate/FEED.md`
