# R392 verdict — parameter-sensitivity mechanism attribution

**Date**: 2026-08-14
**Status**: completed — `MECHANISM-MIXED`
**Type**: experiment
**Wall**: <1h

## TL;DR

R392 validly closes Q-0109 positive through CLM-1105: the sealed eight-arm
parameter-perturbation bank reproduces R391's two positive-real roots exactly
in the reference arm and attributes them to coupled REGF2 loops
(MECHANISM-MIXED) — VSM inertia path, power sensing/signal chain, and voltage
outer PI jointly — with no single parameter isolated.

## Questions opened

- (none)

## Questions closed

- Q-0109 closes positive by CLM-1105: the two positive-real local modes are
  jointly carried by multiple coupled REGF2 internal loops; the exclusive
  voltage-outer-PI attribution of the second mode is not supported.

## Questions advanced

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R392.md`

## 给 PI 的话

**发生了什么**：针对上一轮发现的两个自发放大方向，这一轮把每台设备的
关键内部参数逐一单独改变并重新检查，所有检查都通过了数值与完整性核验，
未改参数的那一次与上一轮的结果完全一致。

**这说明什么**：没有哪一个单独的参数在承载这些方向，至少三处内部环节
共同参与，而且无论怎么改，自发放大都没有消失；这说明问题是这套模型
内部多处环节互相影响造成的，不是单一环节出错。但这只是参数敏感性
证据，不能认定哪个环节是病因，也不涉及真实设备是否安全。

**下一步做什么**：这套默认配置的诊断价值到此为止；继续追病因（例如
直接断开某条回路）必须另立计划并明确授权，在此之前不再开展任何实验。
