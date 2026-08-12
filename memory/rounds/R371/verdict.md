# R371 verdict — per-VSG energy-port design passes

**Date**: 2026-08-12
**Status**: completed
**Type**: analysis
**Wall**: ~2h

## TL;DR

The source-bound four-actor/four-VSG/four-port power-to-torque and achieved-energy design contract passes, so one minimal physical object gate is eligible; no ANDES trajectory, actuator authority, controller result, or training is authorized.  CLM-1000 records the bounded static result and preserves the direct-M/D stop.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R371.md`

## 给 PI 的话

**发生了什么**：新的功率调节入口已经按每台设备分别接好，并把功率命令、入口设定、实际作用和能量收支彻底分开。审查过程中还补上了两个容易制造假成功的保护：能量只能按实际作用结算，动作数量不对时必须立即报错。

**这说明什么**：这条新线已经摆脱了旧方案中“学习对象和实际受控对象不一致”的设计问题，可以进入真实仿真的最小检查；但现在通过的只是设计和接口检查，还不能说明控制有效，更不能说明多设备学习有收益。

**下一步做什么**：只做最小真实仿真，依次检查零动作不改变原系统、单台命令只作用于对应设备、方向和时序正确、实际功率与能量账本一致。任何一项失败就停止修正对象；全部通过后才进入确定性控制和剩余改进空间检查，仍不开始训练。
