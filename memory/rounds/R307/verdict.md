# R307 verdict — Stage-1 invalid on algebraic residual

**Date**: 2026-08-03
**Status**: completed — INVALID-STAGE1-EXECUTION
**Type**: experiment
**Wall**: ~2h

## TL;DR

R307 is INVALID-STAGE1-EXECUTION because every nonzero pulse trace breached the frozen algebraic-residual gate. All positive authority, linearity, coupling, and EVAL outputs remain blocked diagnostics; no predictor, controller, or training gate opens.

## Questions opened (this round)
- Q-0064 — diagnose the TDS solve/readback contract with one prospective worst-case canary.

## Questions closed (this round)
- Q-0063 — closed-negative by CLM-0745; Stage 1 produced no valid positive evidence.

## Questions advanced (this round, status unchanged)
- (none)

## 给 PI 的话

**这周干了啥**：把模型优先线路推进到第二个小门，封存并一次跑完三个工作点、四个功率坐标的正负脉冲，同时让 EVAL 检查分布式边动作是否真的执行。

**结果（一句话）**：27 条都跑完，功率符号、SOC、零和边动作和局部线性都没露馅，但 24 条非零脉冲全部超过预先写死的代数残差门，最坏 2.80e-6 对门槛 1e-8，所以本轮必须判 INVALID。

**意外**：零输入基线仍在 3.77e-9 以内，问题只在动态脉冲和恢复段出现；这更像 TDS 求解容差或残差读回时点没对齐，而不是已经证明 ESD1 没有执行权。EVAL 还暴露了一个 paired-sign 元数据问题，已用单独封存、无重跑的离线 amendment 修正。

**我默认下一步做**：不开完整 Stage 1，更不训练。先查清 ANDES 2.0.0 的 Newton 容差和 `dae.g` 更新语义，再只跑最坏 OP1 edge-2 negative 加零基线的小 canary，门槛仍保持 1e-8。

**你想插一脚就说**：如果你希望把会议标题先改得更保守，或认为应直接停止这条 ESD1 功率路径，现在可以改方向；否则我按 Q-0064 做最小诊断。

Feed: `paper/decoupling_marl_model_first/reports/R307.md`
