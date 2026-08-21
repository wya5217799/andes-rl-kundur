# R391 verdict — positive-real local-model stop

**Date**: 2026-08-14
**Status**: completed — `STOP-REGF2-POSITIVE-REAL-GUARD`
**Type**: sealed science-identical mechanism correction
**Wall**: <1h

## TL;DR

R391 validly answers Q-0108 positive through CLM-1100. Two independently
initialized no-time-advance arms reproduce the same finite 64 by 64 reduced
matrix, the same leading real root `+46.41533383454654 s^-1`, and a second
material real root `+4.606789511264594 s^-1`. All integrity, equilibrium,
independent-spectrum, conditioning, and reproduction guards pass. The exact
stock-REGF2 route stops before authority, controller, or learning work.

## Questions opened

- (none)

## Questions closed

- Q-0108 closes positive by CLM-1100: the exact initialized ANDES model
  contains reproducible local positive-real growing directions before
  simulation time advances.

## Questions advanced

- (none)

## Evidence boundary

The result strongly disfavors time stepping or the two tested initialization
tolerances as the sole explanation for R389's growing trace. It does not prove
physical-converter instability, identify a causal feedback loop, or establish
global/nonlinear stability, safety, authority, decoupling, controller value,
learning value, topology generalization, EMT/HIL behavior, or deployment.

Feed: `paper/converter_vsg_pq_decoupling/reports/R391.md`

## 给 PI 的话

**发生了什么**：在不推进动态过程的两次独立检查中，初始状态完全一致，但都发现两个明显的自发放大方向；所有读取和数值核验都通过。

**这说明什么**：先前曲线的快速增长不是单靠时间步进造成的，这套默认设备配置在当前工作点不适合继续做控制和学习试验；但这不能说明真实设备一定会失稳。

**下一步做什么**：停止这套默认配置并保留结果；如果继续研究，必须另立计划去检查内部环节或更换设备模型，不能直接进入控制和学习方案。
