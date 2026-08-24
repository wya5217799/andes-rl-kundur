# R478 verdict — corrected M/D base-convention revalidation completed: invariants green, energy-port candidate fails every family

**Date**: 2026-08-25
**Status**: completed
**Type**: experiment
**Wall**: ~26h span (planning + six authority generations); <1h simulator execution

## TL;DR

R478 delivered the corrected M/D base-convention implementation: the offline invariants flipped red-to-green (6 of 7 red pre-fix; the telemetry invariant already held) and the V4 regression re-locked; the three repair6 energy-port formal banks executed with owner approval and full integrity; the R408 bandpass candidate failed every registered gate (HELDOUT-FAIL plus BLOCKS-FAIL 0/6), so the candidate route is terminal and direct-M/D training remains closed.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0112 remains open (information-level margin program); neither solved nor closed here.

Feed: `paper/yang_md_decoupling_marl/reports/R478.md`

## 给 PI 的话

**发生了什么**：本轮修了一个参数换算错误——同一组参数在初始化时被重复换算,导致运行时数值减半、零动作也会漂移。修复后,离线检验里之前失败的现在全部通过,剩下一个本来就没问题;旧版本回归检验重新锁绿。经你批准,三组正式仿真全部跑完,结果复核全部通过。候选控制器在它没见过的检验数据上被判负,另外两组共六个格子全部没过,对区域间差异的压制效果几乎为零,离及格线差一截。

**这说明什么**：修复本身有效,证据链干净;但这套候选控制路线被正式判死,后续训练不能开。这个负结论有正面价值:它排除了一个明确候选,而不是否定整个方向——还有排队的检验在等。

**下一步做什么**：默认关掉本轮,马上跑排队的小型检验(约两分钟),把完整结论交给你再定后继路线;大型因子实验继续关闭,直到你明确批准。任何校验指纹对不上就立即停下查证,不重试。
