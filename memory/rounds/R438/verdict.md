# R438 verdict — SAC 消息通道 2x2 隔离: 观测通道是消息增量的主要载体

**Date**: 2026-08-19
**Status**: completed
**Type**: experiment
**Wall**: ~6h

## TL;DR

R438 用 2x2 通道隔离（观测 vs 奖励）定位 R431 SAC 家族正消息对比的机制：
观测通道单独存在时复现消息侧扰动改善，奖励通道单独存在时停留在无消息
侧；交叉端点未干净分离，判定 BOUNDED-UNCLASSIFIED（方向性 OBS 倾向）。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R438.md`

## 给 PI 的话

**发生了什么**：之前发现"让机组互通消息"在一种学习器上有正面效果、在
另一种上反而有害，但不知道正面效果到底来自哪里。这轮把"消息"拆成两个
独立通道做对照实验：一个通道是观测里能看到邻居的信息，另一个通道是
奖励里对邻居表现的依赖——分别单独开启，看哪个能复现正面效果。

**这说明什么**：结果是"观测通道"单独开启时能复现大部分正面效果，
"奖励通道"单独开启时基本没有贡献。也就是说，消息的正面价值主要来自
"能看见邻居在干什么"这个信息本身，而不是来自"奖励鼓励你顾及邻居"。
不过第二个指标没有干净地分开，所以这是方向性结论，还不能算完全定位。

**下一步做什么**：这一环收尾归档，把"消息价值主要来自观测信息"写进
论文讨论；继续处理剩余实验环的收尾。
