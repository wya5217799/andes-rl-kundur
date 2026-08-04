# R296 verdict -- relative-RoCoF boundary no-go

**Date**: 2026-08-02
**Status**: RELATIVE-ROCOF-NO-GO
**Type**: experiment
**Claim**: CLM-0690
**Question**: Q-0053 -> closed-negative

## TL;DR

R296 validates strictly local zero-sum relative-RoCoF execution and favorable
differential-endpoint movement, but the strongest frozen arm misses the 1%
fast-IAE gate by 0.0029 percentage points; it remains a development failure.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0053 -> closed-negative by CLM-0690.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：给四个显式本地 DAPI agent 各加了独立的滤波 RoCoF 状态，只交换邻居标量，并在边上形成反对称有功残差。增益按 1.135 Hz 目标模态推导成原同步动作的 25% 和 50%，不是盲扫；三组共完成 12 条密封轨迹。

**结果（一句话）**：25% 和 50% 残差使快速区间 IAE 分别改善 0.499% 和 0.9971%，同步损失分别改善约 1.00% 和 1.93%，公共与物理守卫全过，但 50% 组仍比预注册 1% 门槛少 0.0029 个百分点，所以必须判 NO-GO。

**意外**：这次残差确实进入了主导差模功率通道，而且强度增加时两个差模端点都同向改善；最大残差总和误差只有 2.6e-18 pu。它不像 R295 那样是“状态变了、动作没变”，而是一个非常接近门槛、但不能靠四舍五入过关的边界结果。

**我默认下一步做**：仍不启动完整 eval。只再做一次物理上清楚的 100% 幅值微型探针；若通过，再用全新工况跑完整 eval；若失败，就停止相位超前增益迭代，转向不同结构而不是继续加点。

**你想插一脚就说**：若你认为 1% 门槛对会议稿过严，可以在论文中完全不使用 R296，而不是事后改阈值；研究流程仍按原门槛走。多网络与单网络比较要等结构候选通过完整 eval 后再进入。

Feed: `results/r296_relative_rocof_probe/FEED.md`
