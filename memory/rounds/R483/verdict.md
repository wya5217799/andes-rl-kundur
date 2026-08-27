# R483 verdict — corrected-card adaptive source factorial: ADAPTIVE-MATERIAL-EFFECT-NOT-ESTABLISHED

**Date**: 2026-08-27
**Status**: completed
**Type**: experiment
**Execution**: 208/208 all-fresh adaptive training cells and 16/16 registered
evaluation shards complete; design valid; integrity pass

## TL;DR

R483 completed the frozen eight-arm by 26-seed corrected-card factorial: none of four registered effects established improvement above the 10% Holm-controlled materiality boundary; the descriptive actor-by-critic estimate was +21.81% (adjusted p=0.118710), all 208 cells reached 43,200 steps without the convergence certificate, and the six-second evaluation did not test the 30-second tail or complete physical guards.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (status unchanged)

- Q-0112 remains open and is not a condition for the current ICEMS revision.

## Formal decision

- Classification: `ADAPTIVE-MATERIAL-EFFECT-NOT-ESTABLISHED`.
- Actor main: -3.50%, Holm-adjusted p=1.0, not rejected.
- Critic main: +5.20%, Holm-adjusted p=1.0, not rejected.
- Actor-by-critic: +21.81%, raw p=0.029677, Holm-adjusted p=0.118710,
  not rejected; descriptive only.
- Critic-by-reward: +4.56%, Holm-adjusted p=1.0, not rejected.
- Adaptive stop: 0/208 convergence certificates; 208/208 stopped at the
  43,200-step maximum. This is a non-convergence result, not an integrity or
  execution failure.
- Registered Phase-3 trade-off field: `NOT_TESTED`; complete corrected-card
  physical-guard evaluation was also not run.

Feed: `paper/yang_md_decoupling_marl/reports/R483.md`

## 给 PI 的话

**发生了什么**：这批学习实验已经完整跑完，所有训练组合和预先约定的评价都有效。四个预先登记的问题里，没有一个在同时控制多重检验后达到“至少改善百分之十”的门槛。一个组合效应看起来约改善了百分之二十二，但证据强度还不够，只能当作描述性现象，不能当成已确认结论。所有模型也都跑到了训练上限，没有触发动态早停条件。

**这说明什么**：这些数据是有分析价值的，而且能可靠支持“在这套固定实验条件下，没有建立超过百分之十的来源或交互效应”。但它不能写成“效果为零”，也不能因为没有触发早停就说训练失败。更关键的是，现有评价只有六秒，没有检查三十秒尾部和完整物理门，所以还不能据此写“这类学习控制已经被证明无法通过完整物理要求”。

**下一步做什么**：按你刚刚的授权，只补一次评价，不重新训练，也不调参。把全部最终模型放到同一组三十秒场景里，并与零动作和已经冻结的确定性方法做同银行的完整物理检查；这项结果出来后，论文就能决定保留受限的学习结论，还是进一步收窄叙事。
