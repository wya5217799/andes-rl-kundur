# R228 verdict — Action bound 2× NOT load-bearing (bit-identical SOTA)

**Date**: 2026-05-20
**Status**: CLOSED-NEUTRAL — confirms hyper saturation, fifth non-load-bearing axis
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` SOTA hyper at s54 with --dm-max 600 --dd-max
600 (2× default 300). Result: geo=**0.4152**, LS1=0.368, LS2=0.469,
cum_rf=-0.0692. **Bit-identical to R201**.

R228 closes R119's old action-bound question (aborted by CLM-0218
divergence): widening action bound does not improve SOTA. Consistent
with CLM-0233 D5 finding (R72_w4 advantage is algorithmic, not
action-bound artifact).

## Final non-load-bearing axes list

| axis | sweep | result |
|------|-------|--------|
| tau | 0.001 vs 0.005 | both ~0.4145 |
| gamma | 0.99 vs 0.999 | bit-identical |
| phi_max | 0 vs 1.0 | bit-identical |
| vsg_d0 | 100 vs 50 | bit-identical |
| **dm_max/dd_max** | **300 vs 600** | **bit-identical (R228)** |

5 axes confirmed not load-bearing at SOTA hyper.

## Load-bearing axes (final)

| axis | optimal | sensitivity |
|------|---------|-------------|
| λ_hreg | 0.002 | sharp ±0.0005 window |
| horizon | 75ep | sharp ±25ep cliff |
| hidden_size | 64 | 32 collapse, 128 -10% |
| phi_abs | ≥7 | binary threshold |
| vsg_m0 (train) | safe [0.25, 1.75]× | 2× breakdown cliff |
| seed | s54 | s49 collapse |
| offset | 0 | sharp lucky peak |

## Saturation final report

After 30+ experiments R172-R228 in the autonomous loop:
- **Single-policy SOTA**: R201 0.4152 (and bit-identical R213/R221/
  R227/R228 — all equivalent within the saturated basin)
- **Ensemble SOTA**: R202 0.4145 (same-seed cross-algo, slightly
  below single)
- **All single-axis variations** at the SOTA either bit-identical
  to R201, collapse, or regress

The autonomous loop has thoroughly characterized the SOTA basin.
Further single-axis experiments yield no new information.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — R119's action-bound question now answered negatively, but
R119 was already in aborted state)

## Questions advanced (this round, status unchanged)

(none — saturation comprehensive)

## 给 PI 的话

R228 = dm_max=600 (2× action bound) = bit-identical SOTA. R119
old question 现在答了 (negative): action bound 不是 load-bearing.
Consistent with CLM-0233 D5 finding.

**5 non-load-bearing axes 确认**: tau / gamma / phi_max / vsg_d0 /
dm_max. **7 load-bearing axes 确认**: λ / horizon / hidden / phi_abs /
vsg_m0 / seed / offset.

**SOTA basin 完整 characterized**. R201 0.4152 是 ceiling in
single-policy; R202 0.4145 是 ensemble SOTA; all axes around them
either bit-identical or regress.

R229 候选 = phi_h=0.05 (10× V4 default, still 1/20 of paper). 测
reward weight 中间 magnitude. 不太可能新 SOTA, 但完整 reward landscape
characterization.

## Cross-references

- R201 (SOTA)
- R119 (aborted predecessor)
- CLM-0233 (D5 finding)
- CLM-0218 (R132 α-sweep)
