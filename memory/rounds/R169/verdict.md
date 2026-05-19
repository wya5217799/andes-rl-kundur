# R169 verdict — hreg λ=0.005 at s54, geo=0.3988 (near baseline)

**Date**: 2026-05-19
**Status**: COMPLETED (retro by R171 Gap 1 detection)
**Type**: research

## TL;DR

td3_lstm_hreg at s54 with λ=0.005 produced geo=0.3988 (LS1=0.334,
LS2=0.477) — within 2% of R72_w4 baseline 0.3908. Part of an
hreg-λ sweep also including R170 (λ=0.003, geo=0.4091). See CLM-0325
for the full sweep finding.

## Questions opened (this round)

(none)

## Questions closed (this round)

(none)

## Questions advanced (this round, status unchanged)

- Q-0014 — adds another single-policy datapoint (almost-but-not-quite
  break) to the algorithmic-side closed-partial finding

## 给 PI 的话

R169 = hreg λ=0.005 at s54, geo=0.3988. 单独看是 unremarkable near-
baseline, 但配 R170 (λ=0.003, geo=0.4091) 形成 hreg-λ scan, **R170 是
项目里最强 single policy** (超过 R100 0.383 +6.8%, 距 R154 ensemble
SOTA 0.4119 只差 0.003)。

这两个 round 是 parallel session 跑了没记的, 被 R166 sweep 当 zombie
标 aborted, 差点把 near-SOTA finding 丢了。R171 Gap 1 (results-orphan
detection) 抓回来。详见 [[CLM-0325]]。

(Retro-written by R171 sweep 2026-05-19; near-SOTA finding rescued.)
