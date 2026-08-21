# R383 verdict — converter-level VSG P/Q-decoupling line registration

**Date**: 2026-08-14
**Status**: completed
**Type**: analysis

## TL;DR

R383 registers `converter-vsg-pq-decoupling` as a separate prospective line,
retains ANDES 2.0.0 and the unchanged Kundur network connectivity, and limits
the next action to a non-learning `REGCV1` object/initialization/`Pref/Qref`
authority gate. No simulator trajectory, controller result, or training
evidence is created.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R383.md`

## Technical disposition

- `CLM-1060` records the trust-S line-separation, scope, and evidence
  non-transfer decision.
- ADR-0016 fixes the unchanged-network/new-device intervention and gate order.
- The route remains F5 object reconstruction informed by F4 methodology; it is
  not another learner family.
- The next evidence round must prospectively open and freeze the `REGCV1`
  object/authority question before any new ANDES trajectory.
- Deterministic P/Q decoupling, residual headroom, MARL, robustness, topology
  generalization, EMT, HIL, and deployment remain untested.

## 给 PI 的话

**发生了什么**：原来的实验已经走到停止点，继续更换设备会把旧结论和新问题混在一起。现在旧成果全部保留，同时另建了一条独立研究路线；电网连接和仿真平台不变，只把研究对象改成每台都能分别接受两种功率指令的设备。本轮没有运行新仿真，也没有训练。

**这说明什么**：新的方向已经有了独立的研究对象、证据边界和停止条件，不会再把过去不同对象上的结果拼在一起。它目前只是一个经过登记的计划，还不能说明新设备能够正常运行，更不能说明设备之间的相互影响已经减小或学习方法有效。

**下一步做什么**：先检查四台设备能否稳定启动和完成仿真，并确认每台设备的两种指令都能产生方向正确、归属清楚的实际响应。任何一项不成立就停止这一方案；全部成立后，才进入不用学习方法的控制比较。
