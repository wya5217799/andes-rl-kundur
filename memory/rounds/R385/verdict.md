# R385 verdict -- structural-absence analysis invalid

**Date**: 2026-08-14
**Status**: completed - `ANALYSIS-INVALID`
**Type**: experiment
**Wall**: 0.44 s formal execution; one invalid compound gate

## TL;DR

R385's immutable classifier reported a reference-mismatch STOP, but the sealed
runner read static-generator `p/q` after TDS replacement instead of at the
prospectively required post-power-flow/pre-init point. The scientific STOP is
invalid; all endpoint observations stay quarantined and R385 is not retried.

## Questions opened (this round)

- Q-0105: structurally clean four-REGCV1 initialization gate.

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0105 remains in flight because R385 is analysis-invalid.

Feed: `paper/converter_vsg_pq_decoupling/reports/R385.md`

## Technical disposition

- The unique formal attempt, record, and STOP classifier output remain
  immutable and hash-bound.
- The runner violated the registered reference endpoint timing; the apparent
  mismatch is not an admissible scientific failure.
- Completed setup, power flow, initialization, short TDS, residual, finite,
  and drift fields remain quarantined under invalidity precedence.
- R385 has no retry, controller, perturbation, training, or manuscript result.
- One successor may repair only the pre-init source snapshot and repeat the
  same sealed gate under a new plan, rehearsal, and seal.

## 给 PI 的话

**发生了什么**：这次系统完成了短时运行，但复核发现，我们把一组用于核对的原始数值取晚了。设备替换已经发生后再读取，导致比较双方不再代表同一时刻，所以机器给出的停止结论无效。

**这说明什么**：现在既不能说新设备能用，也不能说它不能用。真正失败的是测量顺序，不是设备本身；本轮产生的数值只能保存，不能写进论文结论，也不能据此开始控制或训练。

**下一步做什么**：本轮不重跑。另开一轮，只修正取值时刻并加入自动核验，网络、设备参数和判定标准全部保持不变；只有重新得到有效结论后，才决定是否继续下一阶段。
