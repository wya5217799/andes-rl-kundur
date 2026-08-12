# R368 verdict — deterministic headroom analysis invalid

**Date**: 2026-08-12
**Status**: completed - ANALYSIS-INVALID
**Type**: experiment
**Wall**: <1h

## TL;DR

R368 completed the frozen development bank but the actuator-mapping validity
guard failed, so CLM-0985 registers only an invalid result; Q-0103 remains open
and no deterministic, oracle, or training conclusion is allowed.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0103 remains open; an outcome-blind analysis-only tolerance correction is
  the sole eligible successor.

Feed: `paper/paralleled_vsg_marl/reports/R368.md`

## 给 PI 的话

**发生了什么**：全部预定组合都正常跑完，没有仿真崩溃，也没有动作超限；但最后核验时，单精度执行与高精度复算之间的微小舍入差超过了事先设得过严的门槛，因此整轮结果被判无效。

**这说明什么**：现在既不能说确定性方法有效，也不能说它无效，更不能据此开始训练。能确认的只有物理运行完整，而数值核验规则还不适合动态动作。

**下一步做什么**：不重复仿真，只根据单精度运算本身的误差上界重新确定核验容差，再对同一批不可变记录做一次独立复核；如果复核仍不通过，就停止这套方案。
