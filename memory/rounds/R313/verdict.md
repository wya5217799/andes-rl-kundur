# R313 verdict - global predictor missed the held-out NRMSE gate

**Date**: 2026-08-03
**Status**: completed - PREDICTOR-NO-GO
**Type**: experiment
**Wall**: ~3h

## TL;DR

R313 validly executed the sealed predictor holdout, but four HP1 edge-0 cases exceeded the 0.15 total-NRMSE ceiling. Retaining measured cross outputs still beat the matched block ablation on all 32 forced records, so the next bounded step is local operating-point interpolation, not cross deletion or controller/MARL work.

## Questions opened (this round)
- Q-0070 - add HP1 only as development data and test one frozen local/simplex predictor on a new untouched holdout.

## Questions closed (this round)
- Q-0069 - closed-negative by CLM-0775.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这周干了啥**：只用 R312 拟合了保留 cross block 的 common/differential predictor，然后在两个新工况、两个新幅值上跑了 34 条封存物理轨迹和 24 条 EVAL 视图。
**结果（一句话）**：执行全有效，但 HP1 的四条 edge-0 轨迹把最大 NRMSE 推到 `0.17496 > 0.15`，所以是 `PREDICTOR-NO-GO`；同时保留 cross block 比硬删 cross 降低了 `97.21%` 的 cross 误差，32/32 获胜。
**意外**：问题不在大幅值，0.025 和 0.065 两层几乎一样；真正薄弱点是全局工况插值，而不是“解耦坐标没用”。
**我默认下一步做**：把已看过的 HP1 只降格为 development 点，另封全新的 holdout，单因子测试 local/simplex interpolation；阈值不放宽，仍不写控制器、分布式智能体或 MARL。
**你想插一脚就说**：当前安全的会议题目是 `Coupling-Aware Common–Differential Modeling of Paralleled VSGs: Signed Authority and Predictor Limits`；原题里的 `Coordination` 和 `Multi-Agent Reinforcement Learning` 仍然没有结果资格。
Feed: `paper/decoupling_marl_model_first/reports/R313.md`
