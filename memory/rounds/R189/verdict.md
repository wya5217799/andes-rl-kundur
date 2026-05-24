# R189 verdict — late-discovered h128 hreg lambda=0.001 result

**Status**: CLOSED-NEGATIVE
**Date**: 2026-05-19

## TL;DR

R189 has no plan file, but a local scored run exists:
`results/r189_w1_hreg_lambda0p001_h128_s54/final_eval_summary.json`.
It scored `geo=0.3963`, `cum_rf=-0.0853`; hidden-size 128 still did not
beat the smaller hreg configuration. This verdict closes the
result-orphan warning.

## Result

- LS1: 0.3495860506280032
- LS2: 0.4491592522690398
- geo: 0.3962572511686828
- cum_rf: -0.08527676977982661

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- The h128 variant added negative evidence against capacity-only tuning
  as a fix for the plateau.

## 给 PI 的话

R189 是另一个 hreg+h128 补账：geo 0.3963 / cum_rf -0.0853。它也没有
超过小模型 hreg，所以只作为历史审计闭环保留。
