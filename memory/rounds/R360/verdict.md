---
round: R360
---
# R360 verdict - flexible non-neural residual gate: no learnable structure

**Date**: 2026-08-07
**Status**: completed - NO-NEIGHBOUR-LEARNABLE-STRUCTURE
**Type**: sealed offline exact-information family gate
**Wall**: <10min

## TL;DR

R360 validly shows that none of the three pre-registered tuning-free non-neural
map families (RBF kernel ridge, k-NN, quadratic polynomial basis) clears both
registered endpoint groups on the exposed development bank. Q-0097 closes
negative by CLM-0950; the preregistered stop fires, the learning route
terminates, and holdout, simulation, and training stay unauthorized.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0097 closed-negative by CLM-0950 for the registered flexible non-neural
  map family on the frozen finite development bank.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/decoupling_marl_model_first/reports/R360.md`

## 给 PI 的话

**发生了什么**：我们把上一轮失败的简单规则，换成三套更灵活但仍不涉及机器学习的规则，用完全相同的信息和物理条件重新检验。三套规则都通过了完整性检查，但都没有达到事先定的效果门槛，共同指标的改善仍不足，而单元间差异指标反而明显变差。

**这说明什么**：这说明问题不在"规则太简单"这一层：在给定的相邻信息里，这三套更灵活的方法同样找不到能同时改善两个指标的规律。按照事先写好的约定，这条学习路线就此停止，不再靠加大计算量或换办法碰运气。

**下一步做什么**：保留已经完成的全部结果与检查记录，不再启动训练或大规模仿真。若将来要换方向，必须先提出一个全新的、可检验的问题，并且说明它与这次失败的机制区别；否则就维持停止状态，把现有成果整理归档。
