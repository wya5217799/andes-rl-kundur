# R474 verdict — owner-ordered abort: external deep review found the same-time P placebo design invalid as written

**Date**: 2026-08-23
**Status**: aborted
**Type**: experiment
**Wall**: ~1.5h (training start to shutdown)

## TL;DR

R474 (U2 same-time-permutation placebo successor) was sealed and launched on 2026-08-23, then stopped by owner order after an external deep review (gpt_pro_r474_placebo_review_deep_20260823) demonstrated the current `pi(i)=(i+2)` diagonal-copy P wiring does not satisfy the guardrail's per-slot pool equality (only the merged channel pool holds), the confirmatory main effects mix old/new training batches with a 2/3 offset coefficient, and the declared "Holm-controlled materiality" is not what the aggregate implements. No R474 training shard completed (48 reused R473 manifests intact, zero fresh shards), so the round supplies no factorial result; successor R475 re-implements the placebo as a row permutation of the authentic N neighbour 4-tuples with an all-fresh 2x2 confirmatory factorial and a direct materiality Holm test.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 [opened R445] remains open; R474 did not reach aggregation.

Feed: `(none; owner-ordered abort before any training shard completed — successor R475 implements the redesigned protocol)`

## 给 PI 的话

**发生了什么**：你安排的对照实验在下午启动后，一份外部深度审查指出实验设计本身有三处硬伤：对照组的信息布线没有达到我们自己定的纯度门槛、新老两批训练数据混在一起会污染结论、统计检验的写法与声明不一致。我核实后确认这些指控属实，按你的决定立即停掉了所有训练进程；由于刚启动不久，没有任何训练单元跑完，损失只有约一个小时的机时。

**这说明什么**：这次不是"跑出来的结果不好"，而是"设计在被检验前就被证明不合格"。好在叫停及时，几乎没有浪费；外部审查同时给了一份可以直接落地的替代方案，比原来的方案更干净、更便宜（训练量反而从六十片降到四十八片）。

**下一步做什么**：按外部方案开新一轮：换成更干净的对照组布线、全部单元同轮重新训练、统计口径按审查意见修正，然后重新走完整的启动流程（设计审查、试运行、封存、正式训练），预计今晚启动、明天出结果，赶得上注册截止。
