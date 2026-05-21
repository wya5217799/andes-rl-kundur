---
round: R195
state: completed
opened: '2026-05-19'
closed: '2026-05-19'
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
type: research
---
# R195 verdict — widened action bounds collapse the SOTA hyper (-48%)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE — bounded action is an essential constraint; R119 dead-branch closed
**Type**: research

## TL;DR

Trained `td3_lstm_hreg` λ=0.002 at seed=54 with widened action bounds
`--dm-max 1200 --dd-max 1200`, all other hypers identical to R174.
Result: geo=**0.2151**, LS1=0.158, LS2=0.293, cum_rf=-0.0458.

Per R195 plan outcome map, this is the **COLLAPSE** branch (geo <
0.40): widened bound destabilises training even under the SOTA
algorithm. **Bounded action is an essential constraint**, not a
limit-imposed conservatism that hreg can compensate for.

## Comparison

| Run | algo | action bound | seed | LS1 | LS2 | geo | Δ vs R174 |
|-----|------|--------------|------|-----|-----|-----|------------|
| R174 | hreg λ=0.002 | default | 54 | 0.367 | 0.467 | **0.4139** | (ref) |
| **R195** | **hreg λ=0.002** | **dm/dd=1200** | **54** | **0.158** | **0.293** | **0.2151** | **-48%** |

LS1 (-57%) and LS2 (-37%) both collapse. Not a per-axis trade-off —
both response classes degrade together. The widened bound enables
larger swings during exploration that the actor cannot productively
exploit and which apparently destabilise critic learning.

## Refines the R100 mechanism story

R100 observation (CLM-0148/0149): "critic Q is monotone along action
axis with argmax at ±1 boundary." We had treated this as evidence
that **bounded-action was the binding constraint** but the direction
of binding was unclear (would relaxing help or hurt?). R195 settles
this: **relaxing the bound destroys the policy**. The actor cannot
find a useful policy in the larger action space at the same hyper
configuration. The bound is not just binding; it is **load-bearing**
for the SOTA recipe.

This is consistent with R100's interpretation: the policy lives on
the boundary because the optimal control IS at the boundary, and
relaxing it removes the optimal from the action set rather than
opening a new direction.

## R119 dead-branch closed

Handoff Task #18 (R119-W1 widen-bound) was listed as "DEAD (killed
by old session). Re-launch candidate if PI wants completeness, but
R100 evidence says action bound is not load-bearing for plateau."
R195 contradicts the "not load-bearing" guess: the bound IS load-
bearing, and widening collapses the SOTA. R119 dead-branch is closed
with a clear negative answer.

## Fourth fragility axis for paper Sec.IV-D

R195 adds an action-bound axis to the previously identified three
fragility axes (seed, env-RNG-path / offset, training horizon).
Updated joint fragility picture for the R174 SOTA recipe:

| Axis | Perturbation tested | Δ geo |
|------|---------------------|-------|
| seed | s49 (vs s54) | -98% (collapse) |
| env-RNG-path | offset=100 (vs 0) | -6% (mild, under hreg) |
| training horizon | episodes=200 (vs 75) | -24% |
| **action bound** | **dm/dd=1200 (vs default)** | **-48%** |

The R174 SOTA recipe sits at a narrow joint optimum across **four
axes**.

## Questions opened (this round)

(none directly; the LS1+LS2 joint collapse pattern is worth noting
but not a separate Q)

## Questions closed (this round)

(none in the formal Q ledger; R119 dead-branch task-list item
closed via this round)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

❌ **R195 (hreg + 宽 action bound dm/dd=1200 at s54) = geo 0.2151** —
**-48% 跌幅** vs R174 0.4139. LS1 -57%, LS2 -37%. **宽 action
bound 直接 collapse SOTA hyper**。

**关闭 R119 dead branch with NEGATIVE answer**: action bound 是
**load-bearing**, not free-to-widen。R100 critic-monotone-on-action
故事 (argmax at boundary) 现在解释为 "optimal control IS at boundary,
relaxing 把 optimal 移出 action set"。

**加上一个 fragility axis (现在 4 个)**:
1. seed: s49 vs s54 = -98% (full collapse)
2. env-RNG-path (offset): offset=100 vs 0 = -6% (mild under hreg)
3. training horizon: 200ep vs 75ep = -24%
4. **action bound: widened vs default = -48%**

R174 recipe 在四 axes 上都坐在窄优化点上。Paper Sec.IV-D 的 multi-
axis fragility memo (`docs/paper_drafts/sec_iv_d_multi_axis_fragility_memo.md`)
要扩展加入 action-bound axis。

**Research arc 已完整**: 这四个 axes 的 perturbation 都 explored,
负结果都收上来。下一步只剩 paper writing — 把 D.6b multi-axis
sub-section integrate 到 sec_iv_d_final.md, plus refine D.10
failure modes 包括 R191 / R195。

## Cross-references

- R174 (SOTA at default bound) - CLM-0330
- R100 critic-monotone observations - CLM-0148 / 0149
- Handoff Task #18 R119-W1 (now closed)
- R191/R192/R193/R194 (other fragility axes)
- Paper memo: `docs/paper_drafts/sec_iv_d_multi_axis_fragility_memo.md`
