# R361 verdict — one-hop neighbour-message learnability gate

**Date**: 2026-08-07
**Status**: completed
**Type**: analysis
**Wall**: ~2h

## TL;DR

R361 extends each edge actor's information path with frozen one-hop
ring-neighbour messages (23-field observation) and retests the four
pre-registered tuning-free non-neural map families on the exposed development
bank; every integrity check passes but all four families fail both endpoint
groups, so the surveyed information-path hypothesis is further weakened and
Q-0098 closes negative with training, simulation, and EVAL unauthorized.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- Q-0098 closed-negative by CLM-0955 (one-hop neighbour-message extension
  does not recover learnable structure on the exposed development bank)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R361.md`

## 给 PI 的话

**发生了什么**：这次把每个设备的"看邻居"能力加强了一档——除了自己两个端点的数据,还允许接收环状网络上相邻两个节点的实时信息,然后在同一批开发场景上,把四种不学习、无调参的映射方式各试了一遍,看它们能不能补出事先证明存在的优化空间。

**这说明什么**：没有达到事先要求。四类映射在加强信息后仍然全部不合格:共同指标的改善最多只到约百分之一点几,离要求的百分之二还差一段;设备间的差异指标不但没改善,反而普遍变差。加强一跳邻居信息这条最有希望的路径,在这一批固定数据上没有带来可学习结构,按事先约定停止该方向;这个结论只针对这一种消息设计和固定数据,不能推广到"任何邻居信息都没用"或"神经网络一定学不会"。

**下一步做什么**：默认不再在这条路上修补。剩下机制上不同的方向还有两个:一是把邻居间的信息升级成对未来轨迹的共享预测,二是给全体设备增设一个共同功率通道再检验物理空间是否扩大;两者都需要单独注册新问题后才能动,我会在开始前先跟你确认再做。
