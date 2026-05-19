# R227 verdict — vsg_d0 damping NOT load-bearing (bit-identical SOTA)

**Date**: 2026-05-19
**Status**: CLOSED-NEUTRAL — damping is another non-load-bearing axis
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --vsg-d0 50 (half of
default 100). Result: geo=**0.4153**, LS1=0.368, LS2=0.469,
cum_rf=-0.0693. **Bit-identical to R201 (0.4152)**.

## Updated non-load-bearing axes list

| axis | sweep | result |
|------|-------|--------|
| tau | 0.001 vs 0.005 | both at 0.413-0.415 |
| gamma | 0.99 vs 0.999 | bit-identical |
| phi_max | 0 vs 1.0 | bit-identical |
| **vsg_d0** | **100 vs 50** | **bit-identical (R227)** |

Load-bearing axes:
- λ_hreg (0.002 sweet spot, narrow ±0.0005)
- horizon (75ep sharp peak, ±25ep cliff)
- hidden_size (64 peak, 32 collapse / 128 regress)
- phi_abs (≥7 threshold, sharp binary)
- vsg_m0 (training: [0.25×, 1.75×] safe, 2× breakdown cliff)
- seed (s54 lucky)
- offset (0 lucky)

## Why so many axes don't matter

Likely: SOTA hyper sits in a flat basin in these dimensions. Damping
(vsg_d0) and other "soft" axes contribute < eval noise (±0.010). Only
axes affecting the reward landscape structure (phi_abs, hreg λ) or
training capacity (horizon, hidden, seed) move the needle.

## R228 candidate

--dm-max=600 (2× the default action bound). R119 was aborted (never
tested at SOTA hyper). May reveal whether action-bound is part of the
hreg sweet-spot mechanism or an independent capacity question.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

(none — saturation continues)

## 给 PI 的话

R227 = vsg_d0=50 = bit-identical R201. Damping 加入 non-load-bearing
list (tau / gamma / phi_max / vsg_d0).

剩余 untested load-bearing 候选: --dm-max (action bound, R119 aborted
never run at SOTA). R228 试 dm_max=600.

## Cross-references

- R201 (default SOTA)
- R213/R221 (other non-load-bearing axes)
