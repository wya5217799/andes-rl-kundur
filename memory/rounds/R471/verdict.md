# R471 verdict — external session ceiling interrupted the second training wave

**Date**: 2026-08-21
**Status**: aborted
**Type**: experiment
**Wall**: ~5h

## TL;DR

R471 completed 16 of 108 training shards with valid 43,200-step hashed outputs,
then the external unified execution session ended while the next 16 shards had
only half checkpoints. No learner/TDS failure was recorded, but the sealed
round is incomplete and supplies no factorial conclusion.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `(none; orchestration-aborted incomplete factorial)`

## 给 PI 的话

**发生了什么**：第一批训练全部正常完成，第二批也运行到一半，但承载长任务的外层会话达到时限后关闭了调度器，完整实验因此没有跑完。

**这说明什么**：已经完成的训练本身有效，故障来自长任务的启动方式；由于整套对照不完整，本轮仍然不能给出科学结论。

**下一步做什么**：在新一轮中逐项核验并复用已经完整完成的数据，排除所有半程文件，只补跑缺失任务，并改用不依赖对话会话寿命的后台调度方式。
