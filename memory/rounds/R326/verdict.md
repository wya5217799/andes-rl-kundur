---
round: R326
---
# R326 verdict - candidate solver completes development but reference recovery blocks admission

**Date**: 2026-08-04
**Status**: completed - SOLVER-REPAIR-NO-GO
**Type**: sealed centralized model-only numerical-admission gate

## TL;DR

R326 passes every identity and deterministic replay guard, and the specialized
solver completes all 64 development cases with valid candidate residuals.
Complete equivalence admission nevertheless fails because the legacy SLSQP
reference does not reproduce eight registered R325 successful prefixes under
the frozen R326 execution environment. The holdout remains inaccessible,
Q-0080 remains open, and no controller-performance, physical,
distributed-agent, learning, or title-result claim is admitted.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0080 - candidate completion and residual adequacy are established on the
  development bank, but the exact successful-prefix equivalence gate remains
  unresolved because eight legacy-reference prefixes are not recovered. One
  isolated scratch intervention on the numerical execution environment is the
  only eligible next diagnostic; R326 itself remains immutable.

Feed: `paper/decoupling_marl_model_first/reports/R326.md`

## 给 PI 的话

**发生了什么**：新的计算方法把全部已知情况都算完了，也没有越过事先规定的限制。但在核对旧记录时，旧方法有八段原本成功的过程没有重现，所以这次正式检查仍判为不通过，未见过的新情况也没有打开。

**这说明什么**：研究路线没有彻底失败，新方法本身也不是这次被否定的对象。真正缺失的是一份条件完全一致的旧结果对照；在补齐之前，还不能说控制方法有效，更不能说保留不同变化之间的联系带来了改善。

**下一步做什么**：只检查这八段旧过程能否在原来的计算条件下重现，新方法、案例、及格规则和论文题目都不改。若能重现，再单独登记一次最小补证；若仍不能重现，就停止沿用这份旧对照，重新设计可验证的比较方法。
