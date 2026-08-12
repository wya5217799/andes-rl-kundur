# R377 verdict — settling-floor rule defect stops high-pass damping gate

**Date**: 2026-08-12
**Status**: completed - STOP-DEVELOPMENT-NO-CANDIDATE (contract-rule floor)
**Type**: experiment
**Wall**: <1h

## TL;DR

R377 executes the high-pass mutual-damping successor gate: identity holds on
all 60 development trajectories, probe cross-response drops to 0.78-0.85x
local (repairing the R376 amplification), and the best candidate reaches
0.962x local differential energy. But every arm's settling time is at the
local floor (1.2 s), so the frozen "at least one dt below local" rule is
unsatisfiable and no candidate is selected; the execution records stay valid
and a correction round reanalyses them.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R377.md`

## 给 PI 的话

**发生了什么**：新一批协同方案跑完了六十条开发轨迹，动作全程没有越过物理约束，机组间的交叉影响反而比只看本机的对照方案降低了约两成，差分能量也略有下降。但所有方案（包括对照本身）的收敛时间都停在同一个下限上，而事先登记的规则要求至少再快一步，这一步在物理上已经不可能。

**这说明什么**：这一次没有选中方案，不是因为新机制无效，而是规则里的一条时间要求写得过严——对照方案本身已经顶到下限，没有更快空间。执行数据本身是有效且干净的，可以继续使用。

**下一步做什么**：把这条不合理的规则修正为"不慢于对照方案"，用同一批有效数据重新走一次选择；若修正后选中方案，再执行保留库测试。修正轮会完整保留这次的正式失败记录，也不会授权训练。
