# R316 verdict — dynamic reduction passes; deterministic design becomes eligible

**Date**: 2026-08-03
**Status**: completed - DYNAMIC-REDUCTION-PASS
**Type**: experiment
**Wall**: ~2h

## TL;DR

R316 validly passes every frozen dynamic-reduction and mismatch gate on 50 new physical records; Q-0071 closes, but controller efficacy, distributed agents, and MARL remain untested.

## Questions opened (this round)
- Q-0072 - synthesize and reject one constrained deterministic common/differential controller offline before any physical closed-loop test.

## Questions closed (this round)
- Q-0071 - closed-positive by CLM-0790.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这轮干了啥**：保持 R315 的 order-10 ERA、开发数据、输入波形和全部科学阈值不变，只预先修正零请求时 achieved-power 的求解器残差容差，并在两套全新工况上一次跑完 50 条 ANDES 轨迹和 36 条 EVAL 视图。

**结果（一句话）**：R316 是 `DYNAMIC-REDUCTION-PASS`；最大 reduced-versus-physical NRMSE 为 `0.07789 <= 0.15`，最大归一化绝对残差为 `0.08370 <= 0.20`，最大谱半径为 `0.989996 <= 0.995`，保留 cross 输出相对删除 cross 降低 `72.24%` 的 aggregate cross-error，并在 48/48 条强迫响应上获胜。

**意外**：R315 暴露的是执行 guard 把约 `1e-7` 量级的求解器残差误判为隐藏动作，不是模型 NO-GO；R316 的单因素修复让所有记录有效，但因为工况也换了，不能把跨轮变化解释为 guard 的因果效果或精度提升。

**我默认下一步做**：先在模型内冻结一个受约束的 deterministic common/differential controller 和一个严格匹配的 baseline，先过极点、约束、R316 mismatch stress 和可识别性门；离线失败就立即停，不直接烧新的 ANDES 闭环银行，更不开始智能体或训练。

**你想插一脚就说**：会议标题继续原样保持 `Decoupling-Oriented Coordination of Paralleled VSGs With Multi-Agent Reinforcement Learning`；当前新增证据只支持动态模型和经验 mismatch 前置门，`Coordination`、分布式智能体和 `Multi-Agent Reinforcement Learning` 仍是待验证方向，不是已获得结论。

Feed: `paper/decoupling_marl_model_first/reports/R316.md`
