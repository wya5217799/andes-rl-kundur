# R180 verdict — late-discovered hreg lambda=0.0025 result

**Status**: CLOSED-PARTIAL
**Date**: 2026-05-19

## TL;DR

R180 has no plan file, but a local scored run exists:
`results/r180_w1_hreg_lambda0p0025_s54/final_eval_summary.json`.
It scored `geo=0.4104`, `cum_rf=-0.0696`, a useful but non-winning
dose-response point. This verdict closes the result-orphan warning.

## Result

- LS1: 0.35691218438510086
- LS2: 0.4718699970418613
- geo: 0.41038536936640635
- cum_rf: -0.06957503179231575

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- hreg lambda dose-response got one fine-sweep point near the observed
  local peak, but the later ledger already carries the aggregate story.

## 给 PI 的话

R180 补上 `lambda=0.0025` 的结果：geo 0.4104 / cum_rf -0.0696。它支持
“峰值在 0.0015-0.002 附近”的旧判断，但没有新增 claim。
