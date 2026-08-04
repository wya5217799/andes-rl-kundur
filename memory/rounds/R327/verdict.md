---
round: R327
---
# R327 verdict - solver adequacy passes and the fixed controller fails development

**Date**: 2026-08-04
**Status**: completed - DEVELOPMENT-NO-GO
**Type**: sealed model-only legacy-reference amendment and controller-admission gate

## TL;DR

R327 validly recovers all eight missing legacy prefixes, closes Q-0080 positive
for specialized-solver adequacy, and then rejects the unchanged controller
because both valid synthesis arms materially worsen the registered development
output metric relative to zero control. Retaining measured cross blocks is
less harmful than deleting them but is not efficacious control. The holdout
remains inaccessible, and Q-0081 opens for a development-only causal diagnosis.

## Questions opened (this round)

- Q-0081 - isolate whether the valid controller's severe output amplification
  begins at state estimation, action sign/timing/map, predicted-versus-realized
  response, or the finite-horizon objective before any repair is eligible.

## Questions closed (this round)

- Q-0080 - closed positive by CLM-0845 for numerical solver adequacy after all
  eight missing prefixes recovered and the combined 64-case gate passed. This
  closure does not pass the controller, which independently reaches
  `DEVELOPMENT-NO-GO`.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/decoupling_marl_model_first/reports/R327.md`

## 给 PI 的话

**发生了什么**：这次把上次缺失的八段旧记录全部补齐，新计算方法也确认能稳定完成全部已知情况。但控制动作真正作用后，两种设计都让波动比完全不控制时更大，所以仍然没有打开未见过的新情况。

**这说明什么**：失败已经不是“算不出来”，也不是动作越过限制，而是控制设计本身把扰动放大了。保留不同变化之间的联系后，结果比强行切断这些联系好一些，但仍然远未及格，因此硬拆开不是修复方向，整条研究路线也没有因此结束。

**下一步做什么**：只挑最差的已知情况，逐步核对看到的状态、算出的动作、预计的下一步变化和实际发生的变化，先判断错误来自状态判断、动作方向与时机，还是短期目标本身。暂时不换模型，不调一批参数，不打开新情况，不训练智能系统，论文题目保持不变。
