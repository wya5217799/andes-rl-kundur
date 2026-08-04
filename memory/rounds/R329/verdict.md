---
round: R329
---
# R329 verdict - fixed disturbance-aware estimator passes development

**Date**: 2026-08-04
**Status**: completed - AUGMENTED-ESTIMATOR-DEVELOPMENT-PASS
**Type**: sealed retained-arm model-only estimator repair

## TL;DR

R329 closes Q-0082 positive for deterministic development admission: one
fixed permitted-signal disturbance-aware estimator passes every unchanged
retained control gate and greatly lowers aggregate reduced-model latent-state
error relative to the valid failed observer parent. Development data selected
the candidate, four cases lack casewise error improvement, the nominal error
poles have little margin, and Q-0083 opens for the untouched registered
holdout and output-mismatch modes before any physical execution.

## Questions opened (this round)

- Q-0083 - test the frozen estimator on the untouched separated-doublet cases
  and five registered output-mismatch modes without any resynthesis, tuning,
  fallback, or post-outcome repair.

## Questions closed (this round)

- Q-0082 - closed positive by CLM-0855 for one fixed estimator's deterministic
  development admission under the reduced-model information contract; no
  holdout, physical, distributed, learning, robustness, or title-result claim
  follows.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `paper/decoupling_marl_model_first/reports/R329.md`

## 给 PI 的话

**发生了什么**：这次不再把外部冲击误认成系统内部变化，而是让状态判断同时记住外部冲击。其他计算和限制都没动。结果全部已知情况都比不控制好，原来会严重放大的问题消失了。

**这说明什么**：这说明前面的失败不是整条路线无效，而是状态判断方式不合适。新方法在已知情况中已经过关，但它是根据这些已知情况选出来的，而且有四种情况的内部判断并非逐项更准，所以还不能说它面对新情况也可靠。

**下一步做什么**：下一步只用从未参与选择的新情况，并人为加入已经事先规定的测量偏差，检查结果是否仍能及格；其余模型、动作、限制和论文题目不变。真实仿真、多个控制单元协同和自动学习继续封闭。
