# R314 verdict — local predictor passes; dynamic mismatch remains

**Date**: 2026-08-03
**Status**: completed - LOCAL-PREDICTOR-PASS
**Type**: experiment
**Wall**: ~2h

## TL;DR

R314 validly passes every frozen local/simplex predictor gate on two new operating conditions, but controller and MARL work remain blocked pending a separate dynamic-mismatch gate.

## Questions opened (this round)
- Q-0071 - freeze and validate one low-order dynamic/modal reduction and mismatch set before controller design.

## Questions closed (this round)
- Q-0070 - closed-positive by CLM-0780.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这周干了啥**：把 R313 的失败工况 HP1 只降格成 development 点，冻结两个 local simplex，然后在 HQ0/HQ1 上重新跑了 34 条全新 ANDES 轨迹和 24 条 EVAL 视图。

**结果（一句话）**：R314 是 `LOCAL-PREDICTOR-PASS`；最大 NRMSE 为 `0.09061 <= 0.15`，保留 cross 输出比硬删 cross 降低 `99.46%` 的 cross 误差，并在 32/32 条强迫响应上获胜。

**意外**：R313 的 `0.17496` 已降到 `0.09061`，但这是“增加 HP1 数据 + local simplex”的组合修复，不能把功劳单独归给 locality；而且 HQ1 最坏误差仍是 HQ0 的约 2.37 倍，动态 mismatch 并不均匀。

**我默认下一步做**：另开一轮冻结低阶动态/模态 reduction 和 mismatch set，加入至少一种非矩形脉冲的全新 holdout；不先写控制器、分布式智能体或 MARL。

**你想插一脚就说**：当前安全会议题目更新为 `Coupling-Retaining Common–Differential Modeling of Paralleled VSGs: Signed Authority and Local Prediction`；`Coordination`、`Distributed Agents`、`Multi-Agent Reinforcement Learning` 仍等后续结果授权。

Feed: `paper/decoupling_marl_model_first/reports/R314.md`
