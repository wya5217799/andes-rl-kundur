# R395 verdict — PPVSM1 correction analysis-invalid (trace-shape seam)

**Date**: 2026-08-14
**Status**: aborted — `ANALYSIS-INVALID`
**Type**: experiment
**Wall**: <1h

## TL;DR

R395's sealed single arm is analysis-invalid by CLM-1120: one residual
trace-shape seam (device-major initial row consumed as signal-major)
invalidates the record while the frozen 0.2-second trajectory converged with
reference deviation 0.0 and the archived 18-value spectrum again shows no
root with Re > 1e-7. Q-0110 stays open.

## Questions opened

- (none)

## Questions closed

- (none)

## Questions advanced

- Q-0110 stays open: the two-unit PPVSM1 object gate remains unanswered.

Feed: `paper/converter_vsg_pq_decoupling/reports/R395.md`

## 给 PI 的话

**发生了什么**：又修掉一处记录毛病后，这一轮在最后一步的数据整理上还
差一个格式对不上的小问题，结果再次作废。至此模型本身的各项检查其实都
已经正常通过，问题全部出在记录仪器的细节上。

**这说明什么**：科学内容每次留下的数值信息都一致地显示新模型没有自发
增长的方向；连续作废反映的是排练没覆盖到最末一步，而不是模型有问题。

**下一步做什么**：把排练直接延伸到整条检查链的末端，让所有记录步骤都
在正式检查前先完整跑一遍；其余不变，再跑一次。
