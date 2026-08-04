# R299 verdict -- fixed retune beats adaptive edge allocation

**Date**: 2026-08-03
**Status**: CLASSICAL-RETUNE
**Type**: experiment
**Claim**: CLM-0705
**Question**: Q-0056 -> closed-negative

## TL;DR

R299 finds that a fixed all-edge gain increase explains the tested headroom;
the finite edge-allocation oracle does not justify adaptive or neural control.

## Questions opened (this round)

- Q-0056 -- edge-local information-value gate after CLM-0700.

## Questions closed (this round)

- Q-0056 -> closed-negative by CLM-0705.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：围绕 R298 的强分布式经典基线，只做了 4 个工况、6 种边增益放置的 24 条快速探针；同时保留全边统一加倍和逐边 outcome oracle，专门区分“普通增益没调够”与“真的需要自适应智能体”。

**结果（一句话）**：全边统一加倍是最佳固定方案，快速区间 IAE 和同步损失比值为 0.9682 和 0.9535；oracle 相对它为 0.99996 和 1.00093，24/24 有效、零和误差最大 6.94e-18。

**意外**：逐边选择看起来有一些局部差异，但几乎没有超过固定加倍方案的净价值；这说明现在直接训练多网络，大概率只是在用神经网络重新发现一个更大的经典增益。

**我默认下一步做**：停止自适应和神经训练，把 `2Kv` 作为唯一候选，直接使用 R299 结果前已封存的 12 个新工况做完整 eval，并重新跑原 `Kv` 与集中式向量 PI 作为新鲜对照。

**你想插一脚就说**：若你希望优先保留 MARL 叙事，可以在正式 eval 后再重新定义一个有真实信息或资源异质性的多网络问题；当前这组结果不支持为了标题硬上网络。

Feed: `results/r299_edge_information_probe/FEED.md`
