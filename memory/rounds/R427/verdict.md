# R427 verdict — 差模通道价值目标归一化压制了估价发散(0.32-1.75,预注册<3命中)、稳住了策略梯度、动作压力红线停止失败;共模频率与峰值红线仍全数失败(CANARY-FAIL 保持)

**Date**: 2026-08-18
**Status**: completed
**Type**: experiment
**Wall**: ~4.5h（训练 9 组 ~2.1h + 评估 ~0.9h + 分类/收尾 ~1.5h；含 Tier-1 筛查 ~0.7h）

## TL;DR

R427 layered the DR-menu P1 critic target normalization (PopArt-style running mean/std on the CD-arm differential-channel TD target with exact output correction, beta 1e-3 / sigma floor 1e-4, common channel verbatim) onto the R425 bundle and met its pre-registered criterion: the original-scale critic divergence is suppressed (Q4/Q1 0.32-1.75 < 3 across six runs, versus R425's 4.65-6.29), the untouched scalar arm still diverges (raw 3.5-7.0, byte-identical to R419), the actor gradients stop vanishing, and the action-stress no-harm guards stop failing across all 36 CD blocks (R425: 12/36). CANARY-FAIL holds because common-frequency and worst-peak no-harm guards still fail in every CD block, endpoints stay ~3.1-3.4x above the unpenalized base, and the message increment is mixed-sign ≈0.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R427.md`

## 给 PI 的话

**发生了什么**：这一轮只加了一件事——把价值网络的学习目标做了一层随训练自动缩放的调节，让它的数值不再越训越大，其余全部照旧。结果按事先写好的判断标准命中：价值网络的数值膨胀被止住了，六个训练起点全部过关，而没做这项处理的对照臂还在膨胀，说明这层修复正好落在病灶上。连带效应是策略梯度的幅度不再萎缩，动作压力类的红线也不再失败——上一轮还剩十二块失败，这一轮全部过关。

**这说明什么**：之前一直挡在训练稳定性前面的是价值网络的数值尺度失控，这一轮把它修住了，训练动力学从此健康。但动作压力过关并不等于约束机制自己收敛——约束的调节权重仍然一上来就顶到上限、读数仍超出阈值两倍多，所以这个过关更多是策略在健康的梯度下自己找到了更温和的动作，而不是约束真正把力用足了。真正剩下的问题是频率恢复：频率类和峰值类红线在每一块里仍然全数失败，端点指标仍停在基准的三倍开外，通信带来的改进测出来基本还是零。

**下一步做什么**：默认方向转向剩下的频率恢复缺口——把力气花在让几台机器步调一致上，或重新审视公共预算这个调节项。另一条已经开门的线是把参照论文的方法原样复现一遍做直接对比，这轮之后它已进入正式准备，随时可以开跑。若您想先确认现在的结论在更多随机起点下是否稳定，也可以先做五起点扩展再定下一轮。
