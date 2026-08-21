# R394 verdict — PPVSM1 correction analysis-invalid (residual seams)

**Date**: 2026-08-14
**Status**: aborted — `ANALYSIS-INVALID`
**Type**: experiment
**Wall**: <1h

## TL;DR

R394's sealed single arm is analysis-invalid by CLM-1115: two residual
instrumentation seams (model-local arrays indexed by global DAE addresses;
Pref/Qref read before initialization) invalidate the record while the
archived 18-value spectrum again shows no root with Re > 1e-7. Q-0110 stays
open; only a further science-identical correction successor may proceed.

## Questions opened

- (none)

## Questions closed

- (none)

## Questions advanced

- Q-0110 stays open: the two-unit PPVSM1 object gate remains unanswered.

Feed: `paper/converter_vsg_pq_decoupling/reports/R394.md`

## 给 PI 的话

**发生了什么**：上一轮修过的三处记录毛病已经修好，但这一轮又暴露两处
藏在更靠后步骤里的读数毛病，结果再次作废。设备模型和网络仍然没有动过。

**这说明什么**：还是仪器缺陷，不是科学失败。作废前留下的数值信息依旧
显示新模型没有自发增长的方向。连续两次作废说明排练环节覆盖得不够深，
需要把排练检查推进到比之前更后面的步骤。

**下一步做什么**：修掉这两处读数毛病，同时把排练范围加深，避免再在
正式检查时才暴露问题；其他一切不变，再跑一次。
