# R244 verdict — SAC default at 75ep COLLAPSES (LS1=LS2=0)

**Date**: 2026-05-20
**Status**: CLOSED-NEGATIVE — SAC default hyper insufficient at 75ep
**Type**: research

## TL;DR

Trained SAC algorithm at s54 with default hyper for 75ep. Result:
geo=**0.0100**, LS1=**0.000**, LS2=**0.000**, cum_rf=-0.2023.
**Full collapse** — bit-identical attractor to other collapse cases.

## Why

SAC's entropy-regularized exploration has different convergence
dynamics than TD3 family. Without LSTM/hreg supports and with only
75ep training budget, SAC cannot escape the LS1=0 attractor. This
is consistent with R72_w4 family's plateau finding: 75ep is calibrated
for TD3-class algorithms with LSTM critic; SAC requires different
hyper/longer training.

Not a useful direction at this hyper budget. Closing without
follow-up SAC experiments.

## Questions opened / closed / advanced

(none)

## 给 PI 的话

🛑 R244 = SAC default 75ep = collapse (LS1=LS2=0). SAC 不适合 this
hyper budget. 跳过 SAC 探索.

R245 候选 = scalar + only phi_abs + 150ep (R239 was +1.1% at 75ep,
看 longer training 能不能再 push).

## Cross-references

- R201 (TD3 hreg SOTA)
- R72_w4 (TD3 scalar baseline)
- CLM-0101 (legacy SAC results in old paper-metric mode)
