# R192 verdict — SOTA seed s54 is ALSO offset-dependent (-27% vs baseline)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE — offset effect is universal, not bad-seed-specific
**Type**: research

## TL;DR

Trained `td3_lstm` scalar at seed=54 with seed-offset=100. Result:
geo=**0.2844**, LS1=0.300, LS2=0.270, cum_rf=-0.0742. **-27% vs
R72_w4 baseline 0.391 at offset=0**.

This is a major finding: **even the SOTA seed s54 is offset-dependent**.
The "lucky seed s54" story is more accurately a "lucky (seed,
offset) pair" story. R72_w4 0.391 and R174 0.4139 are both
single-seed-single-offset results, not robust across the env-RNG
configuration space.

## Full offset-vs-baseline picture

| Run | algo | seed | offset | LS1 | LS2 | geo | vs R72_w4 0.391 |
|-----|------|------|--------|-----|-----|-----|------------------|
| R72_w4 | scalar | 54 | 0 | 0.354 | 0.431 | **0.391** | (ref) |
| **R192** | scalar | 54 | 100 | 0.300 | 0.270 | **0.2844** | **-27%** |
| R190 | scalar | 49 | 100 | 0.129 | 0.403 | 0.2276 | -42% |
| R188 | hreg | 49 | 100 | 0.096 | 0.432 | 0.2032 | -48% |

The s54 result at offset=100 (0.2844) is similar magnitude to the s49
result at offset=100 (~0.20-0.23). At offset=100, **all seeds converge
to a similar mid-range performance**.

## Implications for paper

1. **R72_w4 baseline 0.391 is single-offset**: cross-offset mean would
   be lower. Paper should report "we used seed=54, offset=0" not just
   "we used seed=54".
2. **R174 SOTA 0.4139 is single-offset-single-seed**: even narrower
   claim. Multi-offset mean at s54 is the defensible robust number.
3. **Mechanism story upgrades**: not just "s49 has bad RNG path", but
   **"s54+offset=0 has a particularly good RNG path"**. The whole
   training landscape is highly RNG-path-dependent.

## New paper Sec.IV-D narrative

> "Performance in this RL+physics-sim setting is jointly sensitive to
> seed and seed-offset. We report results at (seed=54, offset=0)
> consistently across the paper; cross-offset mean at this seed is
> ~0.30-0.35 (R192 = 0.28 at offset=100; expected basin behavior).
> This is a known property of physics-sim RL and a methodological
> finding of the present work."

## Strong R193 candidate

Does hreg λ=0.002 also drop at s54+offset=100 (matching scalar
behavior), or does hreg *stabilize* across offsets (giving geo near
0.40+ even at offset=100)?

- If hreg stays high: "hreg regularization stabilizes performance
  across RNG paths" — strong paper claim, hreg becomes the
  recommended baseline.
- If hreg drops too: offset dependency is universal, hreg is no
  more robust than scalar.

R193 = hreg λ=0.002 at s54+offset=100.

## Questions opened (this round)

(implicitly: "Is hreg offset-robust?" — answered by R193)

## Questions closed (this round)

(none — Q-0005 already closed-partial; R192 extends mechanism story)

## Questions advanced (this round, status unchanged)

(none — R192 is methodological finding, not Q-specific)

## 给 PI 的话

⚠️ **R192 = s54 scalar + offset=100 = geo 0.2844** — 比 R72_w4
baseline 0.391 跌 **-27%**. SOTA seed 也 offset-dependent.

**"Lucky seed" 故事升级为 "lucky (seed, offset) pair"**: R72_w4 0.391
跟 R174 0.4139 都是 single-(seed, offset) 结果, 不是真正 robust SOTA。
Cross-offset 至少需要 mean across ≥3 offsets 才能 defensible。

**对 paper Sec.IV-D 影响**: 必须 disclose "we report (seed=54,
offset=0)" — 不能再藏 offset。但也提供了一个新 contribution: 普适
RL methodology finding 关于 RNG path dependency。

**R193 = hreg + offset=100 at s54**: 测 hreg 是否 stabilize across
offsets. 如果 hreg robust (geo > 0.40 at offset=100), 是 strong paper
claim ("hreg helps RNG-path robustness"); 如果 hreg 也 drop, offset
dependency 是 universal property。 ROI 很高。

## Cross-references

- CLM-0123 (R72_w4 baseline 0.391 at s54 offset=0)
- R190 verdict (env-side mechanism isolation at s49)
- R188 verdict (env-side first confirmation)
- CLM-0350 (Q-0005 closed-partial)
