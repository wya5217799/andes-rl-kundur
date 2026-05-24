# R173 verdict — late-discovered hreg lambda=0.001 result

**Status**: CLOSED-NEGATIVE
**Date**: 2026-05-19

## TL;DR

R173 was auto-GC'd as reserved-empty, but a local scored run exists:
`results/r173_w1_hreg_lambda0p001_s54/final_eval_summary.json`.
It scored `geo=0.4064`, `cum_rf=-0.0686`, below the R174 local peak
frame. This is ledger closure only; no new CLM is minted.

## Result

- LS1: 0.3644384481915247
- LS2: 0.45309669071035874
- geo: 0.40635680730510515
- cum_rf: -0.06857841558159367

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- hreg lambda dose-response got one additional measured point, but the
  conclusion is already covered by the later dose-response ledger.

## 给 PI 的话

R173 只是补账。盘里有 `lambda=0.001, seed=54` 的 scored run，分数是
geo 0.4064 / cum_rf -0.0686。它没有超过 R174 附近的峰值，所以不单独开
claim；这个 verdict 只负责让结果目录不再是孤儿。
