# R416 verdict — A3 规则池扩充 + 预言机：21 法则仍零余量

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~1.5h

## TL;DR

R416 (soft-spot A3) expanded the deterministic family to 21 laws: the
development gate selects the new km3_kd2 law, the PI law is excluded on
the common-mode guard, the oracle still finds zero headroom on all four
evaluation profiles, and the nine-law re-evaluation reproduces R399
bit-consistently.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R416.md`

## 给 PI 的话

**发生了什么**：我把手工设计的那批规则从九种扩充到二十一种——把增益
网格加密，又新加了一种带积分环节的规则——在完全相同的场景上重跑，并
且把原来那九种当作校验基准。校验结果与历史记录完全一致，说明整批数据
可信。

**这说明什么**：扩大的规则池里确实找到了一个比原基准略强的规则（两个
指标都再强百分之三左右），但"看见结果再选"的预言机在这二十一种规则里
依然挑不出任何额外提升，新加的积分型规则因为让全体设备的同步频率变差
直接出局。"这个有限规则池里没有剩余空间"的结论从九种推广到了二十一
种，论文的这条支点更硬了。

**下一步做什么**：四块补充实验全部完成。接下来把四轮的新结论按门禁写
进论文正文（幅度稳健性、接线稳健性、新数据块边界、规则池推广），标记
计划清单的完成状态，跑完全套校验后交整夜总结。
