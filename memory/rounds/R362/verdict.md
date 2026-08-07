# R362 verdict — shared-prediction (DMPC-style) learnability gate

**Date**: 2026-08-07
**Status**: completed
**Type**: analysis
**Wall**: ~2h

## TL;DR

R362 upgrades the one-hop neighbour message from snapshot states to frozen
R341-model causal prediction trajectories (23-field observation) and retests
the four pre-registered tuning-free non-neural map families on the exposed
development bank; every integrity check passes but all four families fail
both endpoint groups, so the surveyed information-path hypothesis is further
weakened across both its snapshot and prediction variants and Q-0099 closes
negative with training, simulation, and EVAL unauthorized.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- Q-0099 closed-negative by CLM-0960 (shared-prediction message extension
  does not recover learnable structure on the exposed development bank)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R362.md`

## 给 PI 的话

**发生了什么**：这次把邻居之间交换的信息从"当前状态"升级成了"对未来的预测"——每个设备收到的邻居消息,不再是邻居此刻的读数,而是用已验证的冻结模型对邻居未来几拍频率走势的推算;其余设定与上一轮完全一致,四种不学习、无调参的映射方式在同一批开发场景上各试了一遍。

**这说明什么**：没有达到事先要求。四类映射在收到预测消息后仍然全部不合格:共同指标的最好改善约百分之一点三,仍低于要求的百分之二;设备间的差异指标全部变差,最差的一类恶化幅度很大。加上前一轮的快照消息,信息路径假说的两个最强变体都被证伪,按事先约定停止该方向;这个结论只适用于这一种预测设计和固定数据,不能推广到"任何信息扩展都没用"或"神经网络一定学不会"。

**下一步做什么**：默认不再在这两条信息扩展路上修补。剩下机制上不同的方向还有两个:一是给全体设备增设共同功率通道,先检验物理空间是否扩大;二是把"训练前可学性门"本身写成方法学贡献。两者都需要单独注册新问题后才能动,我会在开始前先跟你确认再做。
