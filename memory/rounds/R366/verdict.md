# R366 verdict — unit-valid per-VSG M/D comparator design

**Date**: 2026-08-12
**Status**: completed
**Type**: analysis
**Wall**: ~2h

## TL;DR

The prospective unit, actuator, local-controller, and deterministic-development contract passes, so one non-learning efficacy/headroom gate is eligible; the full MARL comparison and training remain blocked until their budgets are frozen and both pretraining stop gates pass.  Q-0102 closes positive under CLM-0980 without any ANDES trajectory or performance claim.

## Questions opened (this round)
- Q-0102 (unit-valid object-matched deterministic comparator and learning stop-gate design)

## Questions closed (this round)
- Q-0102 closed-positive by CLM-0980 (deterministic development eligible; full learning comparison still blocked)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R366.md`

## 给 PI 的话

**发生了什么**：我们把旧系统里不一致的频率尺度统一到了实际系统采用的尺度，也把控制入口固定为每台设备各自调节两个参数。旧的功率控制、统一动作和按连接边分配动作都没有混进来；所有后续方法还必须经过同一套限幅和变化速度约束。

**这说明什么**：下一步的确定性对照实验现在可以公平地做，但还不能开始训练。学习方法的规模、训练量、调参量、筛选方式和最终测试集合尚未冻结，而且尚未证明确定性方法之后还存在值得学习的动态改进空间。

**下一步做什么**：先用固定的一小组确定性控制方案做非学习实验，同时用一个不训练的上界检验证明仍有额外且随时间变化的改进空间。只要确定性方案没有明显改善，或上界没有留下足够空间，就立即停止这套方案，不启动训练。
