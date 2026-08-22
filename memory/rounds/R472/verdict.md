# R472 verdict — owner-ordered shutdown at 96/108 valid training shards

**Date**: 2026-08-22
**Status**: aborted
**Type**: experiment
**Wall**: ~15h

## TL;DR

R472 completed 96 of 108 training shards with valid 43,200-step hashed outputs before the owner ordered a shutdown to power off the host; the remaining 12 shards are incomplete and a structural-only shutdown inventory was frozen for reuse. No learner/TDS failure was recorded, but the sealed round is incomplete and supplies no factorial conclusion; a successor round must reuse the 96 valid shards and complete the rest.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 [opened R445] remains open; R472 did not reach the aggregation stage that could address it.

## Feed

`(none; owner-ordered shutdown, incomplete factorial — successor round completes the design)`

## 给 PI 的话

**发生了什么**：这次实验跑到接近尾声时你安排暂停关机，我按你的要求停掉了全部训练进程，并把已经完成的单元逐项核对、冻结成清单后保存；整个过程没有读取或解读任何实验结果。

**这说明什么**：已经完成的部分占全部训练任务的将近九成，而且每一份都通过了完整性校验、可以安全复用；但由于对照组没有凑齐，这次仍然不能给出任何科学结论，剩余部分要靠接续实验补完。

**下一步做什么**：接续实验直接复用已经完成的单元，只补跑缺失的一小部分，然后做评估和汇总分析；接续时结论只能按既定边界解读，不能超出范围。
