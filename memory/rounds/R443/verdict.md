# R443 verdict — Q-0026 disposition: lazy-extraction loop signal census, closed negative

**Date**: 2026-08-20
**Status**: completed
**Type**: analysis
**Wall**: ~20 min

## TL;DR

Q-0026 关闭为 negative: 自 R260 以来 claims 中 `extracted_from: NOTE-NNNN`
提取标记为 0, 而 16 个 plan / 8 个 verdict 引用 NOTE — 索引是发现面,
不是 claim 提取管线。

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0026 closed-negative @ R443, by CLM-1375 — Will the Archive Index
  actually be queried (lazy-extraction loop signal)?: no extraction
  signal since R260 (0 `extracted_from` lines repo-wide; 16 plans +
  8 verdicts cite notes; 30 notes alive) — the index is a discovery
  surface, not a claim-extraction pipeline.

## Questions advanced (this round, status unchanged)

- (none)

Feed: `results/research_loop/r443_q0026_disposition/FEED.md`

## 给 PI 的话

**发生了什么**：处理了最后一个挂账的老问题——问的是"项目里的知识索引到底有没有被人真正用起来"。我把所有历史记录翻了一遍,统计了三种使用痕迹:正式的证据引用、写计划时的引用、写结案报告时的引用。

**这说明什么**：答案很明确:索引里的条目确实会被查阅(写计划时引用了十几次),但从开这个问题到现在,没有任何一条正式研究结论把索引条目标记为"从这里提取出来的"。也就是说,这套索引起的是"查阅字典"的作用,不是"生产线"的作用——它没坏,但它没有变成当初设想的自动提取流程。这个问题按实际情况关闭,不再挂着。

**下一步做什么**：这件事到此收尾。三件事全部处理完:悬空的轮次已归档、代码问题已关闭、索引问题已关闭。我做最后一遍全库校验,然后向你汇报最终结果。
