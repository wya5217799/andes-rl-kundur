# R393 verdict — PPVSM1 gate analysis-invalid (instrumentation defects)

**Date**: 2026-08-14
**Status**: aborted — `ANALYSIS-INVALID`
**Type**: experiment
**Wall**: <1h

## TL;DR

R393's sealed single arm is analysis-invalid by CLM-1110: three
instrumentation seams (variable readback via Model.get, unfrozen 0.2-second
horizon, post-init source snapshot) invalidate the record while the archived
18-value spectrum shows no root with Re > 1e-7. Q-0110 stays open; only a
science-identical correction successor may repair the seams.

## Questions opened

- (none)

## Questions closed

- (none)

## Questions advanced

- Q-0110 stays open: the two-unit PPVSM1 object gate remains unanswered.

Feed: `paper/converter_vsg_pq_decoupling/reports/R393.md`

## 给 PI 的话

**发生了什么**：新设备模型的第一轮正式检查已经跑完，但记录仪器的三处
小毛病让这轮结果作废：一处读数方式用错、一处检查时长没按约定设成最短
时长、一处参考快照取晚了。模型和网络本身都没有改动。

**这说明什么**：这是仪器缺陷，不是科学失败。作废前留下的数值信息里，
新模型没有任何自发增长的方向，这是个好兆头，但按规矩这轮不能当作结论。

**下一步做什么**：只修这三处记录毛病、其他一概不变，再跑一次同样的
检查；修好之前不进入任何新环节。
