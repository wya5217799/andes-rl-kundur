# R387 verdict -- signed-authority analysis invalid

**Date**: 2026-08-14
**Status**: completed - `ANALYSIS-INVALID`
**Type**: experiment
**Wall**: 10.44 s formal execution; 17-arm invalid compound gate

## TL;DR

R387 attempted and captured the complete signed authority bank, but its sealed
trajectory schema confuses canonical JSON key order with bus identity, assumes
the native stored array contains an initialization row that ANDES does not
store, and has no scientific branch for an advanced partial trajectory. The
formal invalid classification is preserved; all physical values stay
quarantined and R387 is not retried.

## Questions opened (this round)

- Q-0106: signed, target-attributed per-device REGCV1 Pref/Qref authority.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0106 remains in flight because R387 is analysis-invalid.

Feed: `paper/converter_vsg_pq_decoupling/reports/R387.md`

## Technical disposition

- The unique formal attempt, 17-arm record, invalid classifier output,
  manifest, and sidecars remain immutable and hash-bound.
- Strict diagnosis isolates three trajectory evidence/taxonomy defects; all
  other source/object/reference/diagnostic/action subchecks pass.
- The zero arm remains within the registered envelope, while all nonzero arms
  show at least a voltage violation and eight terminate without convergence;
  these values are diagnostic warnings only and cannot support a scientific
  STOP under the invalid compound record.
- R387 has no retry, controller, training, threshold change, or manuscript
  result. One successor may repair only bus-identity semantics, explicit
  initial capture, and typed advanced partial termination.

## 给 PI 的话

**发生了什么**：十七组测试已经完成，但复核发现，保存顺序和起始时刻的判断与软件真实输出不一致，而且运行到一半提前停止的情况被归错了类别，所以本轮结论无效。

**这说明什么**：现在不能说方案通过，也不能说方案失败。原始记录确实显示，所有非零操作都越过了至少一项边界，半数测试提前停止，但这些只能作为强烈警报，不能写进论文结论。

**下一步做什么**：本轮不重跑。另开一轮，只修正记录和判定方式，网络、设备、参数、操作幅度和全部标准保持不变；取得有效结论后，再决定停止当前设备方案还是进入下一阶段。
