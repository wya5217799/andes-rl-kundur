---
round: R339
---
# R339 verdict - full-DAE separate-input bridge candidate allowed

**Date**: 2026-08-04
**Status**: completed - ALLOW-CANDIDATE
**Type**: source-bound full-DAE input-bridge diagnosis

## TL;DR

R339 validly allows the full-DAE separate-input order-12 candidate to enter one
separately sealed fresh model-validation round. The descriptor, independent
input derivatives, exposed-bank nonlinear replay, and internal reduction gates
all pass, but no fresh validation or controller claim exists.

## Questions opened (this round)
- Q-0089 - test the frozen candidate on a separately sealed fresh nonlinear
  model-validation bank before any controller work.

## Questions closed (this round)
- Q-0087 - closed partial by CLM-0890: the full separate-input formulation is
  sufficient on exposed records, while unique component attribution and fresh
  validity remain unresolved.

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/decoupling_marl_model_first/reports/R339.md`

## 给 PI 的话

**发生了什么**：我们把原来将不同位置混在一起的处理方式改成逐个计算每个位置在完整仿真中的影响，并在两种已经看过的运行状态上重新检查。新方法全部达到事先定下的要求，原来的明显误差消失，压缩后的版本也通过了检查。

**这说明什么**：这说明先前的问题确实与过度合并不同位置的影响有关，新路线值得继续。但这两种运行状态都已经被看过，所以还不能把这次通过当成全新的验证，也不能据此宣称控制方法或学习方法有效。

**下一步做什么**：下一步只用事先锁定、此前没有看过的运行状态检验这套候选方案。它通过后才能讨论控制；如果不通过，就立即停止并查清失败原因。
