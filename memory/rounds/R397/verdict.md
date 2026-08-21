# R397 verdict — PPVSM1 two-unit signed P/Q authority stop

**Date**: 2026-08-14
**Status**: completed — `STOP-PPVSM1-SIGNED-AUTHORITY`
**Type**: experiment
**Wall**: <1h

## TL;DR

R397 validly closes Q-0111 negative through CLM-1130: the sealed nine-arm
bank stops the frozen two-unit PPVSM1 cell at signed authority because a
signed Pref step at PPVSM1_1 moves the non-target device's Pe at least as
far as the target's own, failing the target-attribution floor while every
other guard passes. The PPVSM1 formulation stops before any controller,
decoupling, or learning work.

## Questions opened

- (none)

## Questions closed

- Q-0111 closes negative by CLM-1130: the two-unit PPVSM1 cell cannot
  establish target-attributed active-power authority for PPVSM1_1 Pref.

## Questions advanced

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R397.md`

## 给 PI 的话

**发生了什么**：在上一轮通过检查的双机对象上，正式做了一组正向和反向的
功率指令测试。指令全部被精确接收，系统每次都正常收敛，电压、电流、
功率都保持在允许范围之内，每台设备也都做出了方向正确的响应。

**这说明什么**：没有达到事先要求。当第一台设备收到有功指令时，第二台
设备的有功变化和第一台一样大，甚至更大，所以在这个连接方式下，无法把
响应明确算到被指令的那一台头上。这个结论只针对当前冻结的双机单元和
运行点，不能说这类设备普遍不可用，也不涉及任何稳定性结论。

**下一步做什么**：按事先约定，这条设计路线在这里停下，不再进入任何
控制或学习相关实验。是否换单元规模、连接方式或工作点重新尝试，需要你
单独决定后再开新的一轮。
