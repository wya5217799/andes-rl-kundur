# R221 verdict — phi_max=1.0 tied with SOTA (R31 shaping not load-bearing)

**Date**: 2026-05-19
**Status**: CLOSED-NEUTRAL — phi_max axis confirms hyper saturation
**Type**: research

## TL;DR

Trained td3_lstm_hreg SOTA hyper at s54 with --phi-max 1.0 (enable
R31 max-disturbance shaping that was previously OFF). Result:
geo=**0.4151**, LS1=0.368, LS2=0.469, cum_rf=-0.0691.

**Bit-identical structurally to R201** (geo 0.4152, LS1=0.368,
LS2=0.469). R31 worst-agent max-disturbance shaping does NOT move
the converged policy at this hyper.

## Saturation report (continued)

Single-axis hyperparameters that DO NOT change SOTA at R201 hyper:
- tau: 0.001 (R174) ≈ 0.005 (R201) [within 0.3%]
- gamma: 0.99 (R201) = 0.999 (R213) [bit-identical]
- **phi_max: 0 (R201) ≈ 1.0 (R221) [within 0.024%]**
- offset: 50 (R194) ≈ 100 (R193) [within 0.2%, both ~0.388]

Single-axis hyperparameters that DO change SOTA:
- λ: 0.002 SOTA, 0.001 / 0.003 sub-optimal
- horizon: 75ep peak, ±25ep drops 10%
- hidden: 64 peak, 32/128 collapse/regress
- phi_abs: ≥10 needed (sharp threshold)
- seed: s54 lucky, s49 collapse
- offset: 0 lucky, 50/100 stable mid-band

## Why marginal axes don't matter

Three explanations consistent with the data:
1. **Deterministic eval**: same actor produces same actions; gradient
   nuances in training don't affect deterministic output
2. **SOTA basin shape**: the optimum is in a flat region wrt these
   axes; small training changes converge to nearby points
3. **Reward landscape dominated by phi_abs/phi_h/phi_d magnitudes**:
   other terms are minor; their gradients are dominated

R31/R33 shaping (phi_max, phi_settle) were designed as "extra"
signals; the SOTA hyper finds the optimum without needing them.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — hyper saturation now thoroughly characterized)

## 给 PI 的话

R221 = phi_max=1.0 = **0.4151** — bit-identical SOTA structure
(LS1/LS2 same as R201). R31 shaping not load-bearing.

**Saturation map**: λ/horizon/hidden/phi_abs/seed/offset 是 load-
bearing; tau/gamma/phi_max 不是. R201 hyper 在 marginal axes 上 flat,
move 不动.

R222 候选 = --phi-settle 1.0 (R33 shaping 也 OFF). 但很可能也 = 0.4152,
单纯确认 saturation. 之后是真没什么新 single-axis 可试了, 应该 pivot
到 paper writing.

## Cross-references

- R201 (SOTA reference)
- R213 (gamma=0.999 bit-identical)
- R31 (original max-shaping design)
- v4_config.py phi_max docstring
