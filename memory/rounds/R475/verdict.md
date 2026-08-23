# R475 verdict — aborted: formal seal and review coverage were not enforced

**Date**: 2026-08-23
**Status**: aborted
**Type**: experiment
**Wall**: ~52 min (formal training start to shutdown)

## TL;DR

R475 was sealed and launched, then stopped after a code review proved that its formal phases called the inherited R470 `load_seal()` instead of an R475-specific verifier. Consequently, the declared R475 plan, power, routing, rehearsal, two reviews, capacity record, and shard lists were not revalidated at each formal phase. The two review artifacts also covered different runner/test hashes, and a post-seal test-only commit changed a sealed source while training was active. Six imported base manifests were present, but no fresh R475 training shard completed. R475 therefore supplies no scientific result; all partial files remain preserved and excluded from interpretation. A successor must implement an R475-specific full seal verifier, executable terminal probes, fail-closed classification, identical two-review hash coverage, a fresh rehearsal, and a new seal before any retry.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 [opened R445] remains open; R475 did not reach a valid aggregate.

Feed: `(none; formal execution invalidated before any fresh training shard completed)`

## 给 PI 的话

**发生了什么**：这轮实验运行约五十二分钟后，代码审查发现启动前的封存检查没有真正检查本轮的全部文件，两份代码审查也没有覆盖同一版代码。我随即停止了所有相关进程，并完整保留已有文件；当时只有六份从上一轮导入的基础记录，没有任何新的训练单元完成。

**这说明什么**：这不是实验结果好坏的问题，而是本轮不具备成为正式证据的资格。继续运行也无法补回启动前已经缺失的审查和封存链，因此现有部分数据不能用于论文结论。

**下一步做什么**：开一个全新的后继轮，先把封存检查、终止条件探针、完整性分类和双审查哈希覆盖修好，再重新试运行、封存和启动。后继轮还会在启动前明确总任务量、预计耗时和中断恢复规则，避免运行后才发现时间与关机风险。
