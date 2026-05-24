# R179 verdict — late-discovered hreg lambda=0.0015 result

**Status**: CLOSED-PARTIAL
**Date**: 2026-05-19

## TL;DR

R179 has no plan file, but a local scored run exists:
`results/r179_w1_hreg_lambda0p0015_s54/final_eval_summary.json`.
It scored `geo=0.4125`, `cum_rf=-0.0689`, a useful but non-winning
dose-response point. This verdict closes the result-orphan warning.

## Result

- LS1: 0.36713717341549496
- LS2: 0.4635720209421503
- geo: 0.41254638701994434
- cum_rf: -0.06892792733232758

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- hreg lambda dose-response got one fine-sweep point near the observed
  local peak, but the later ledger already carries the aggregate story.

## 给 PI 的话

R179 补上 `lambda=0.0015` 的结果：geo 0.4125 / cum_rf -0.0689。它是
有用的 fine-sweep 点，但没有形成新的结论；这里只做审计闭环。
