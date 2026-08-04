# R321 verdict - exact pole target is rejected

**Date**: 2026-08-03
**Status**: completed - POLE-TARGET-NO-GO
**Type**: model-only controller examination
**Wall**: ~2h

## TL;DR

R321 validly rejects the exact R320 fixed pole-targeted observer-feedback construction after it passes nominal, finite, governed, mismatch, and replay gates but fails every-case absolute output-energy and mean matched retained-cross improvement gates.

## Questions opened (this round)
- Q-0077 - diagnose gain conditioning, corrected-observer transients, governor projection, and their interaction using development-only evidence before selecting at most one analytic repair.

## Questions closed (this round)
- Q-0076 - closed-negative by CLM-0815.

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R321.md`

## 给 PI 的话

**发生了什么**：上一轮固定好的方案参加了原来的电脑考试。它没有越过设备允许的范围，计算过程也完整，但设备发出的动作几乎每一步都被限制。所有新情况都没有把波动压小，最好的一次也比完全不采取措施坏一百多倍；平均来看，承认各种变化会相互影响的方案反而比忽略这种影响的对照差约百分之二十九。

**这说明什么**：把内部变化强行调快，虽然在数学检查中合格，却不能保证实际调节有效。这条固定方案已经明确失败，不能继续修改后重考。动作几乎一直被限制与失败同时出现，但现在还不能确定主要原因是命令过猛、对状态的判断偏差，还是两者共同造成；也不能据此否定相互影响本身，更不能证明多个控制单元自行配合或学习的方法有效。

**下一步做什么**：下一步只用早已公开的练习情况，把“命令过猛、判断偏差、设备限制”三种可能拆开检查，不再利用这次新题的答案挑方案。找不到明确原因就停止这条设计；如果找到，也只固定一个新的办法，再用全新的题目考试。论文题目保持不变，暂时仍不做真实仿真，也不让多个控制单元自己学习配合办法。
