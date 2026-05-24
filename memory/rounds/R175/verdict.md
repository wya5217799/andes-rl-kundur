# R175 verdict — late-discovered hreg lambda=0.004 result

**Status**: CLOSED-NEGATIVE
**Date**: 2026-05-19

## TL;DR

R175 was auto-GC'd as reserved-empty, but a local scored run exists:
`results/r175_w1_hreg_lambda0p004_s54/final_eval_summary.json`.
It scored `geo=0.4049`, `cum_rf=-0.0702`, below the useful
dose-response region. This is ledger closure only; no new CLM is minted.

## Result

- LS1: 0.34410181617191093
- LS2: 0.4765272732308978
- geo: 0.40493690888112477
- cum_rf: -0.07017657178185809

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- hreg lambda dose-response got one additional measured point, but the
  conclusion is already covered by the later dose-response ledger.

## 给 PI 的话

R175 也是补账。`lambda=0.004, seed=54` 的 scored run 是 geo 0.4049 /
cum_rf -0.0702，没有改变 hreg dose-response 结论。这个 round 不产生新
claim，只关闭本地 result orphan。
