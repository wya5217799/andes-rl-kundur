# R315 verdict — execution guard invalidates dynamic-reduction metrics

**Date**: 2026-08-03
**Status**: completed - INVALID-DYNAMIC-REDUCTION-VALIDATION
**Type**: experiment
**Wall**: ~1h

## TL;DR

R315 completed its 50-trace bank and 36-view EVAL audit, but the formal physical-record validator rejected all 48 forced records; no model metric is admissible and Q-0071 remains open.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0071 - repair the action-withdrawal achieved-power guard prospectively, then validate the unchanged dynamic-model family on new operating conditions.

## 给 PI 的话

**这轮干了啥**：冻结了 order-10 ERA、两套新工况和 impulse/triangle/bipolar 三种非矩形输入，一次跑完 50 条 ANDES 轨迹，再对 36 条 edge 记录跑了 EVAL。

**结果（一句话）**：R315 是 `INVALID-DYNAMIC-REDUCTION-VALIDATION`，不是模型 `NO-GO`；正式 guard 把 48/48 条强迫记录都判无效，所以任何 NRMSE、mismatch 或 cross 数字都不能解释。

**意外**：零轨迹、模型来源和 EVAL 都通过；单条 canary 显示动作请求、命令和读回归零后，已实现功率还残留约 `3.5e-7` p.u.，而新 guard 错用了 `1e-8` 的理想零阈值。

**我默认下一步做**：不改模型阶次、波形和科学阈值，只在新一轮预先冻结一个求解器残差容差，并换两套全新工况重跑完整 holdout；R315 本身不修补、不重解释。

**你想插一脚就说**：会议标题继续保持 `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`，但这轮没有给 Coordination、分布式智能体或 MARL 增加证据。

Feed: `paper/decoupling_marl_model_first/reports/R315.md`
