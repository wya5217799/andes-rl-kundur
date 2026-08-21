# R384 verdict — four-REGCV1 formulation stops at native initialization

**Date**: 2026-08-14
**Status**: completed — `STOP-REGCV1-OBJECT-INITIALIZATION`
**Type**: experiment
**Wall**: 1.25 s formal execution; no valid TDS trajectory

## TL;DR

R384 validly constructs four one-to-one `REGCV1` objects and verifies isolated
direct writes at zero-valued `Pref/Qref` references, but native TDS
initialization has `test_ok=false`. No time-domain step executes, so this
registered formulation stops before dynamic authority, control, or learning.

## Questions opened (this round)

- Q-0104: four-`REGCV1` object, interface, and initialization gate.

## Questions closed (this round)

- Q-0104 closed negative by CLM-1065.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/converter_vsg_pq_decoupling/reports/R384.md`

## Technical disposition

- The formal attempt is unique, sealed, create-only, and not retried.
- Object mapping, frozen network inventory, status-zero source-chain readback,
  and isolated direct software writes pass.
- All observed `Pref/Qref` baselines are zero, so interface identity is not
  nonzero dynamic authority evidence.
- Setup and power flow pass, but the native initialization validity test fails;
  no finite-trajectory or drift evidence exists.
- `REGCV1` receives no signed-authority, deterministic-decoupling, headroom,
  information, MARL, robustness, or topology experiment under this route.
- Another converter model or true source-model removal requires a separate
  prospective route decision; R384 does not authorize it.
- The immutable analysis's static `next_gate` auxiliary value conflicts with
  the sealed STOP branch. Publication audit excludes that metadata field; it
  is not successor authority and the formal artifact remains unmodified.

## 给 PI 的话

**发生了什么**：四台新设备都接到了原来的四个发电位置，网络连接没有变化，每台的两类指令也能单独写入并恢复。但是系统在进入动态计算前没有通过自身检查，所以没有产生任何有效动态过程。

**这说明什么**：设备接得上、静态计算能完成，并不等于动态模型已经成立。当前这套替换方法不能继续用于控制比较，更不能开始训练；它也不能说明整个研究方向或现有平台都不可行。

**下一步做什么**：按预先规则停止当前设备方案，不在本轮改参数或重跑。若以后继续，需要先另行论证一种实质不同的设备建模方案，再从启动检查重新开始。
