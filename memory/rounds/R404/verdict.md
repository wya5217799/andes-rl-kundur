# R404 verdict — repaired successor fails disclosed development gate

**Date**: 2026-08-15
**Status**: completed — `SCRATCH-FAIL`
**Type**: experiment
**Wall**: <1h

## TL;DR

R404 returns SCRATCH-FAIL by CLM-1175: the no-message repaired arm passes every
development guard, but the message arm fails the frozen common-mode no-harm
ceiling despite passing differential, action, slew, diagnostic, and physical
validity guards. The repaired learner route stops without tuning or unseen work.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R404.md`

## 给 PI 的话

**发生了什么**：修好记录问题后，我们完全按原来的设置重新完成了小规模
试验。不传递设备间消息的办法全部过关；传递消息的办法虽然让设备之间的
差异表现更好、动作也平稳很多，但所有设备共同偏移的表现比强常规办法差了
约七成，超过事先允许的五成上限。

**这说明什么**：修复确实解决了动作过猛和记录失效，但没有解决完整方法
最关键的共同表现保护要求。按照开跑前的规则，这条学习路线没有通过，论文
题目所需要的核心效果证据仍然不存在；这也不能扩大成“传消息普遍有害”。

**下一步做什么**：停止继续训练、调权重或更换学习方法，也不进入新的考核
场景。接下来只处理论文路线：放弃现有题目，或者把这条被严格终止的路线写成
边界清楚的负结果说明；没有新的研究决策前不再增加实验。
