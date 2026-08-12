# R375 verdict — deterministic formulation stopped by held-out physical guard

**Date**: 2026-08-12
**Status**: completed - STOP-UNSAFE-CONTROL
**Type**: experiment
**Wall**: <1h

## TL;DR

R375 corrects the identity contract and completes the frozen deterministic
comparison, but every selected-controller held-out trajectory triggers the
energy-port ramp-projection guard, so the formulation stops without training.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R375.md`

## 给 PI 的话

**发生了什么**：上次的设备名称错误已经修好，重新核验后也确实找到了一个表现较好的方案，但它在全部保留测试中都碰到了事先规定的动作变化边界。

**这说明什么**：这套方案虽然看起来能减弱机组之间的相互影响，却没有通过物理约束，所以不能算成功，也不能作为后续学习的可靠基础。

**下一步做什么**：停止这套方案和原定后续训练；题目继续保留，但下一步必须先提出一个真正不同、能在保留测试中同时改善效果并满足物理边界的方案。
