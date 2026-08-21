# R396 verdict — PPVSM1 two-unit object gate pass

**Date**: 2026-08-14
**Status**: completed — `PPVSM1-OBJECT-PASS`
**Type**: experiment
**Wall**: <1h

## TL;DR

R396 validly closes Q-0110 positive through CLM-1125: the two-unit
projected-passive dual-droop VSM object initializes cleanly, holds the
frozen 0.2-second zero-input stationarity envelope, and its 18-by-18 reduced
spectrum has no positive-real mode and exactly one allowed network
common-angle degeneracy. Only a signed P/Q authority gate opens next.

## Questions opened

- (none)

## Questions closed

- Q-0110 closes positive by CLM-1125: the redesigned two-unit object passes
  initialization, stationarity, and spectrum guards.

## Questions advanced

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R396.md`

## 给 PI 的话

**发生了什么**：新的设备模型在两次设备组成的小系统上通过了第一道正式
检查：它能够正常搭建和初始化，在没有收到任何指令的检查窗口内保持
稳定，内部也没有之前那种自发增长或永远漂移的方向。

**这说明什么**：之前发现的结构性缺陷已经被这套新设计去掉了，新对象在
当前工作点上具备继续研究的资格。这只是一道入门检查，还没有证明它可以
被正确指挥，也没有证明它比传统方案更好。

**下一步做什么**：默认继续推进下一道检查，即验证每台设备的有功和无功
指令是否能被正确接收和执行；在这道检查通过之前，不做任何控制对比或
学习相关的实验。
