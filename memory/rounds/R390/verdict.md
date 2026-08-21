# R390 verdict — equilibrium/EIG analysis invalid

**Date**: 2026-08-14
**Status**: completed — ANALYSIS-INVALID
**Type**: sealed mechanism-only evidence gate
**Wall**: <1h

## TL;DR

R390 completed its sealed two-arm record, but two evidence-adapter/classifier
defects made `arm_integrity=false`. CLM-1095 records only the invalid attempt.
Q-0108 remains open, R390 cannot be retried, and no equilibrium, eigenvalue,
stability, authority, controller, or learning conclusion is allowed.

## Questions opened (this round)

- Q-0108 remains in flight after the invalid attempt.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0108 requires a separately registered successor with only the diagnosed
  evidence-adapter and state-name validation corrections.

Feed: `paper/converter_vsg_pq_decoupling/reports/R390.md`

## 给 PI 的话

**发生了什么**：两次预定检查都完成了，也没有运行动态过程或控制算法，但最后核验发现，程序读取内部矩阵和核对状态名称的方法有两处错误，所以这一轮被判为无效。

**这说明什么**：这次既不能说明系统存在局部发散方向，也不能说明不存在；能够确认的只是问题出在证据读取和名称核对，而不是已经得到一个可信的物理结论。

**下一步做什么**：保留这次失败记录，不重复本轮；另开一次范围完全相同的后续检查，只修复这两处读取与核对错误，重新预演、审查和封存后再执行。

