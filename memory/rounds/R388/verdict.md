# R388 verdict -- valid negative signed-authority gate

**Date**: 2026-08-14
**Status**: completed - `STOP-REGCV1-SIGNED-AUTHORITY`
**Type**: experiment
**Wall**: 10.45 s formal execution; 17-arm corrected compound gate

## TL;DR

R388 validly stops the exact four-REGCV1 formulation: direct writes are exact
and the zero arm is admissible, but every nonzero arm crosses the registered
electrical envelope and eight end with native nonconvergence.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0106 closed-negative by CLM-1085: the exact REGCV1/card/port formulation
  fails signed per-device Pref/Qref authority qualification.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R388.md`

## Technical disposition

- The integrity-only correction succeeds: record integrity, source/reference,
  diagnostics, initial/native trace capture, finite values, and partial-
  termination taxonomy are valid.
- The scientific gate fails at solver/electrical response after exact direct
  action application. No terminal response or paired-separation conclusion is
  issued for the mixed complete/partial bank.
- Stop the current REGCV1 formulation without tuning, retry, controller,
  training, threshold relaxation, or model substitution. Another device/card/
  port is a new route decision and repeats qualification.

## 给 PI 的话

**发生了什么**：修正记录方式后，重新完成了同一组严格测试。没有操作时系统表现正常；一旦逐台施加正向或反向调节，所有测试都会超出至少一项事先规定的运行范围，其中约一半还会在结束前停止。

**这说明什么**：问题不在指令写错，也不在初始状态，而在这套设备方案、设置方法和操作方式组合后的实际表现。它没有达到进入下一阶段的最低条件；但这不代表所有同类设备方案都不可行。

**下一步做什么**：停止当前方案，不缩小操作幅度、不放宽标准、不靠修改设置补救。若继续这篇研究，应先单独决定是否换用更合适的设备方案或操作方式，并从设备构造、初始状态和双向调节能力重新逐级验证。
