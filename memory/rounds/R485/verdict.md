# R485 verdict — corrected 60-Hz all-fresh learners qualify on endpoints only

**Date**: 2026-08-31
**Status**: completed
**Type**: experiment

## TL;DR

R485 completed with the hash-valid formal classification `VALID-MIXED`.
Corrected 60-Hz all-fresh learners show endpoint-only qualification and no
material source effect established, while direct M/D passes its separate
fresh-bank gate. The result closes large compute and supports only a finite-
benchmark endpoint/command-activity separation.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0112 remains open and is not answered by this finite-bank time-domain
  factorial.

Feed: `paper/yang_md_decoupling_marl/reports/R485.md`

## 给 PI 的话

**发生了什么**：最后一轮全新训练和三十秒评价已经完整结束。部分学习方案改善了两项响应指标，但没有一个同时通过全部要求；参照方法在全部新测试工况中通过。

**这说明什么**：在当前系统和固定测试范围内，学习方案存在“响应变好但控制指令幅度和变化过大”的明显矛盾，不能据此宣称整体优于参照方法，也不能把这项检查解释成硬件有害或安全失败。不同信息来源是否带来稳定改善也没有被证明。

**下一步做什么**：停止所有大规模计算，不再补跑或调参。只把论文的数字、图表和措辞更新为本轮结果，明确结论只适用于当前系统和测试范围，更新后再做一次证据、专业内容和投稿材料检查。
