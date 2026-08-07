# R340 verdict - INVALID fresh nonlinear validation attempt

**Date**: 2026-08-05
**Status**: completed - INVALID
**Type**: experiment
**Wall**: ~3.5h

## TL;DR

R340 is INVALID because a sealed signed-load profile violated the runtime
nonnegative-load guard before the complete validation bank and manifest were
produced. The failure is retained without retry, supplies no predictor
evidence, and leaves Q-0089 open for a prospectively sealed successor round.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0089 remains open: R340 produced an engineering-invalid attempt rather
  than a valid predictor pass or failure; CLM-0895 requires a new sealed
  attempt and prohibits reuse or retry of R340.

Feed: `paper/decoupling_marl_model_first/reports/R340.md`

## 给 PI 的话

**发生了什么**：这次新测试没有跑完。一个事先安排的用电变化会让用电量降到零以下，保护检查因此终止了运行；失败被完整保留，没有重跑。

**这说明什么**：这次结果不能说明预测方法是好是坏，也不能支持控制、协同或学习方面的结论。它只暴露出正式开跑前对测试条件的可行性检查不够完整。

**下一步做什么**：另开一次全新的测试，先逐项确认所有用电变化都不会越过允许范围，再做一次很短的试跑；两步都通过后才固定全量条件。任一步有问题就立即停止，不进入后续控制和学习。
