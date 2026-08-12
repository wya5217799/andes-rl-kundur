# R378 verdict — high-pass damping stops at frozen differential threshold

**Date**: 2026-08-12
**Status**: completed - STOP-NO-DIFFERENTIAL-BENEFIT
**Type**: experiment
**Wall**: <1h

## TL;DR

R378 corrects the single unsatisfiable settling rule, reanalyses the
immutable R377 development bank, selects the high-pass candidate, and
executes the held-out bank once: all physical guards and no-harm ceilings
pass, but the differential-energy improvement over the local arm (0.962x)
misses the frozen 0.95 threshold, so the Gate B-2 successor stops without
training.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R378.md`

## 给 PI 的话

**发生了什么**：修正了上轮那条不合理的收敛时间规则后，用同一批有效数据重新选择了方案，并执行了保留库测试。所选方案在保留库上通过了全部物理约束和交叉影响上限，机间振荡能量比完全不控制时下降了约两成，比只看本机的对照也低了一点，交叉影响更是明显降低。

**这说明什么**：方案方向是对的，物理上完全干净，但机间振荡能量的改善幅度没有达到事先冻结的门槛，差约一个百分点。按事先定好的规则，这算没通过，不能进入下一步学习或调整参数。

**下一步做什么**：停止当前方案族，学习仍不授权。要继续只能先提出一个真正不同的协同机制并重新登记契约；否则就接受"邻居协同在此问题上改善不足"的结论。
