---
round: R194
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R194 verdict — offset basin at s54 hreg is monotonic from 0 (no peak beyond default)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE-FOR-SOTA, POSITIVE-FOR-MECHANISM
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at seed=54, seed-offset=50. Result:
geo=**0.3882**, LS1=0.312, LS2=0.483, cum_rf=-0.1015.

Per R194 plan outcome map:
- offset=50 result lies in **INTERMEDIATE range (0.3875 < 0.3882
  < 0.4139)** → **basin is monotonic** from offset=0 outward, with
  steep initial drop (0→50: -6.2%) then plateau (50→100: -0.2%).

**No new SOTA from offset search**. The "lucky offset" search is
unproductive in the [0, 100] window. R174 at offset=0 remains the
single-config peak.

## Three-point offset basin at s54 hreg

| Run | offset | LS1 | LS2 | geo | Δ vs R174 (offset=0) |
|-----|--------|-----|-----|-----|----------------------|
| R174 | 0 | 0.367 | 0.467 | **0.4139** (SOTA) | (ref) |
| **R194** | **50** | **0.312** | **0.483** | **0.3882** | **-6.2%** |
| R193 | 100 | 0.362 | 0.415 | 0.3875 | -6.4% |

**Interpretation**: offset=0 is a sharp local peak; performance drops
~6% by offset=50 and stays at ~0.388 through offset=100. The "good
basin" at (s54, offset=0) is narrow.

## Cross-offset robust SOTA (now 3 points)

- mean across {0, 50, 100} = (0.4139 + 0.3882 + 0.3875) / 3 = **0.3965**
- stdev = **0.015** (vs scalar single-offset variance ≥0.054)
- peak = 0.4139 at offset=0

**Defensible robust SOTA for paper: 0.40 ± 0.02** (3-offset hreg λ=0.002
mean at s54), with single-config peak 0.4139.

This is more defensible than the single-(seed, offset)-tuned "lucky"
0.4139, and frames the contribution honestly.

## Interesting LS2 inversion

R194 LS2 = **0.483** is the **highest LS2 ever observed at s54 hreg**:
- R174 (offset=0): LS2 = 0.467
- R194 (offset=50): LS2 = 0.483 ← peak
- R193 (offset=100): LS2 = 0.415

But R194 LS1 = 0.312 (lowest of three) drags geo down.

Possible mechanism: offset=50 puts the actor in a state where
loose-load-step recovery (LS2) is easier learned, but disturbance
recovery (LS1) is harder. Hints at LS1-vs-LS2 axis trade-off across
RNG paths — could be a paper sub-finding if explored further (but
not the focus right now).

## R195 in-flight — orthogonal axis

R195 plan: hreg + wide action bound (dm-max=1200, dd-max=1200) at
seed=54. Tests if the R119-killed action-bound axis matters under
hreg. Result pending (~10 min from now). Will be a separate verdict.

## Questions opened (this round)

(none directly; LS1-vs-LS2 axis trade-off observation noted for
potential future Q)

## Questions closed (this round)

(none — Q-0005 already closed-partial; R194 fills out offset basin
data)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

**R194 = hreg s54+offset=50 = geo 0.3882** — 在 R193 (offset=100,
0.3875) 和 R174 (offset=0, 0.4139) 之间, **intermediate**. Offset
basin **从 0 出发单调下降**, 但 0→50 跌得快 (-6.2%), 50→100 基本
flat (-0.2%)。

**没新 SOTA 从 offset sweep**. R174 在 offset=0 仍 single-config 峰值。

**Cross-offset robust SOTA 3-point**:
- mean across {0, 50, 100} = **0.3965**
- stdev = **0.015**
- peak = 0.4139

**Paper defensible 数字**: "robust 0.40 ± 0.02 hreg, peak 0.4139 single-
config" — 比 single-(seed,offset) 数字 honest 很多。

**意外观察 LS2 反转**: R194 LS2 = 0.483 (s54 hreg 史上最高 LS2),
但 LS1 = 0.312 拉低 geo。说明 offset axis 在 LS1-vs-LS2 之间有
trade-off, 不只是 absolute scaling。可以做 paper 副 finding 但优先
级低。

**R195 (在跑)**: hreg + 宽 action bound (dm/dd-max=1200) at s54.
测 R119-killed action-bound axis 是不是 load-bearing under hreg。
~10 min 后落地, 单独 verdict。

## Cross-references

- R174 (offset=0 SOTA 0.4139) - CLM-0330
- R193 (offset=100 0.3875) - CLM-0370
- R192 (scalar offset=100 0.2844) - CLM-0365
- R190/R188 (env-side mechanism at s49) - CLM-0355/CLM-0350
- R195 (sister round, in-flight, wide action bound)
