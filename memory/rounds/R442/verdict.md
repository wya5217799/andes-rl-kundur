# R442 verdict — Q-0004 disposition: absorb-into-V4 declined, docstring fixed, regression green

**Date**: 2026-08-20
**Status**: completed
**Type**: infrastructure
**Wall**: ~1h

## TL;DR

Q-0004 关闭为 negative-by-decision: base_env absorb-into-V4 重构不执行
(54 处路径绑定 + 4 处审计行号 + 过时执行包 + 零研究价值), 改为修正 V4
docstring 矛盾, WSL 1e-9 回归 3/3 绿, 论文路径行为零变化。

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0004 closed-negative @ R442, by CLM-1370 — AndesBaseEnv
  absorb-into-V4 (complete AD-01): full refactor not executed
  (reference-surface census: 49 evidence sha fields, 54 path refs,
  4 audit line bindings across sealed evidence; stale R46 package);
  V4 docstring contradiction fixed instead; 1e-9 no-control regression
  3/3 PASSED, behavior-neutral.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `results/research_loop/r442_q0004_disposition/FEED.md`

## 给 PI 的话

**发生了什么**：处理了一个挂了几百轮的老问题——要不要把环境代码做一次合并式重构。我先把现状摸了一遍:现在这个重构的牵连面比当初开问题时大了很多,几十处已归档的证据记录都指着这个文件,还有审计文档按行号引用它,而当初写好的执行方案里依赖的一个文件已经不存在了。于是我没有动手重构,改为把代码里一段自相矛盾的说明文字改准确,并在仿真环境里重跑了行为一致性校验。

**这说明什么**：重构的代价(要动几十处证据记录、有破坏论文复现的风险)远大于收益(只是读代码时少跳一个文件),所以如实把它记为"评估后不执行",理由完整归档。说明文字已修正,误导消除;行为校验在极高精度下全部通过,论文依赖的复现能力完全不受影响。这个老问题就此正式关闭。

**下一步做什么**：接着处理剩下的最后一个老问题(关于笔记索引是否被真正使用),全部收尾后统一向你汇报。
