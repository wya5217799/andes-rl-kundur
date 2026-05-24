# R187 verdict — late-discovered h128 hreg lambda=0.002 result

**Status**: CLOSED-NEGATIVE
**Date**: 2026-05-19

## TL;DR

R187 has no plan file, but a local scored run exists:
`results/r187_w1_hreg_lambda0p002_h128_s54/final_eval_summary.json`.
It scored `geo=0.3692`, `cum_rf=-0.0835`; hidden-size 128 did not help
this hreg path. This verdict closes the result-orphan warning.

## Result

- LS1: 0.3060968046297594
- LS2: 0.44519885171276385
- geo: 0.36915301154685864
- cum_rf: -0.08350705779732884

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- The h128 variant added negative evidence against capacity-only tuning
  as a fix for the plateau.

## 给 PI 的话

R187 是 hreg+h128 补账：geo 0.3692 / cum_rf -0.0835。hidden-size 128
没有救这个方向，只是补齐 orphan result 的审计记录。
