# R137 verdict — Honest post-mortem of R134-R136 chain rediscovery

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (post-mortem acknowledges project's pre-existing multi-controller strategy)
**Type**: documentation audit + correction
**Wall**: ~30 min

## TL;DR

This session's R134 → R135 → R136 chain claimed to discover novel
SOTA findings. R137 audit reveals all three findings were ALREADY
documented by the project:

- **CLM-0118 (R70)**: r67_w2a IS the deliberately-chosen paper §IV-C
  cum_rf SOTA (cum_rf=-0.119 sum). R134's "hidden SOTA" was not hidden.
- **CLM-0131 (R75)**: R75 W2 s59 IS the geo SOTA (0.4301), already
  promoted from R72_w4 by the project. R135 re-discovered it.
- **CLM-0131 maintains DUAL SOTAs**: R72_w4 = paper Fig 7 canonical
  (P_balance=0.96, 4-agent visually balanced); R75 W2 s59 = geo SOTA
  numeric. Multi-controller strategy CLM-0118 accommodates both.

R136's "r74_w3 strictly dominates R72_w4 SOTA" framing was wrong —
R72_w4 isn't the geo-SOTA, it's the paper-figure canonical.

R137 = honest acknowledgement. R134-R136 work is reinterpreted as
INDEPENDENT VERIFICATION of CLM-0118 + CLM-0131, not new discovery.

Zero ANDES.

## What happened

I joined the session without auditing recent project documentation.
R134 saw r67_w2a in cached summaries with strong cum_rf, framed it as
"hidden". R135 fresh-scored ckpts, saw r75_w2_s59 geo=0.430, framed
it as "new SOTA". R136 compared r74_w3 to R72_w4, framed as "strict
dominance".

In reality:
- R75 verdict CLM-0131 ALREADY explicitly states R75 W2 s59 is the
  new geo SOTA at 0.4301
- R70 CLM-0118 ALREADY states r67/TD3 R67 is the cum_rf paper-metric
  SOTA at -0.119
- R75 verdict EXPLICITLY says "Paper Fig 7 canonical: R72 W4 s54
  (CLM-0123, P_bal=0.96). Single SOTA numeric: R75 W2 s59
  (v3.1=0.4301). Multi-controller paper strategy (CLM-0118) accommodates both."

The project tracks two roles for "SOTA":
1. **Paper Fig 7 canonical** = R72_w4_s54 (visually clean for figure)
2. **Single geo SOTA numeric** = R75_w2_s59 (peak metric)

Plus the paper-metric (cum_rf) candidate is r67_w2a (TD3 R67) per CLM-0118.

My R134-R136 conflated these roles repeatedly.

## What's salvageable

Three genuinely novel contributions remain:

1. **N=91 Pearson r(geo, cum_rf) = +0.533** — quantitative correlation
   statistic the project hadn't computed
2. **Degenerate attractor cluster characterisation**: r67_w2a + warm-h_0
   both at (geo≈0.025, cum_rf≈-0.031), discrete from LSTM cluster
   (geo≈0.41, cum_rf≈-0.068). Visualised in R136 figure.
3. **Stale-scoring methodology issue**: cached `_summary.json` files
   from R57-R69 era use older paper_grade_axes scoring; fresh
   `evaluate_trace` gives different numbers. This is real and may
   warrant a project-wide re-score sweep.

## What's invalid

- "Hidden cum_rf SOTA" framing (R134 / CLM-0243) — superseded
- "Fresh-geo SOTA discovery" framing (R135 / CLM-0250) — re-discovery of CLM-0131
- "Strict dominance over R72_w4" framing (R136 / CLM-0254) — wrong baseline
- All PI briefings R134-R136 that imply "project missed X"

## Lesson

Before claiming "discovery" against project documentation, AUDIT the
documentation first. The R134 verdict's follow-up "audit R72_w4 vs
r69_w3 declaration discrepancy" was the right idea — I should have
done it BEFORE making the "hidden SOTA" claim, not after.

CLM-0118 / CLM-0131 / CLM-0123 are the authoritative SOTA framework.
Any new "metric finding" claim must cite these.

## Decision

R137 closes the R134-R136 chain. The R136 figure (anchor_scatter.png)
remains useful for paper Sec.IV-D once captioned correctly:

> "Project's dual-SOTA strategy visualised in (cum_rf × geo) plane.
> R72_w4 (paper Fig 7 canonical) and R75 W2 s59 (geo SOTA) occupy the
> LSTM Pareto frontier. r67_w2a (paper Sec.IV-C cum_rf SOTA per
> CLM-0118) and warm-h_0 inference both fall in a discrete degenerate
> attractor cluster — they achieve better cum_rf at catastrophic geo
> cost. The discrete cluster structure (no smooth Pareto curve
> connecting clusters) is the new finding from this session."

Net new contribution to paper: the visualisation + cluster discreteness
statement. NOT the SOTA-pivot claim.

## Infrastructure changes

不动: any code, V4, ckpt, test, R134-R136 artefacts.

新建:
- `memory/rounds/R137/{plan.md, verdict.md}`
- `memory/claims/CLM-0255.md` (post-mortem decision)

## Cross-references

- CLM-0118 (R70 multi-controller strategy) — pre-existing framework
- CLM-0131 (R75 geo SOTA promotion) — pre-existing record
- CLM-0123 (R72_w4 paper Fig 7 P_balance=0.96) — pre-existing canonical
- CLM-0243 / CLM-0250 / CLM-0254 (R134/R135/R136 chain) — re-discoveries
- CLM-0260 (this round; CLM-0255 race-collided to R124+R127+R129)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** — sharper framing: the geo plateau is at 0.430 (R75 W2 s59,
  CLM-0131); cum_rf plateau is at -0.119 (TD3 R67, CLM-0118). Both
  long-standing. No new SOTA above these in any session R86-R137.

## 给 PI 的话

**这周干了啥**：你说"继续". 我去 audit R74 / R75 verdict 想看为啥 r74_w3 没被 promote. 结果发现 **R75 W2 s59 已经被 R75 verdict 标 NEW SOTA at 0.4301** (CLM-0131), 而且 CLM-0118 已经说 r67_w2a / TD3 R67 是 paper §IV-C cum_rf SOTA at -0.119. 我 R134 / R135 / R136 整条链全是 **re-discovery**, 不是 novel finding. honest post-mortem.

**结果（一句话, painful self-correction）**: 项目 deliberately 用 **dual-SOTA strategy** (CLM-0118 + CLM-0131):
- **R72_w4 = paper Fig 7 canonical** (P_balance=0.96 视觉干净), NOT geo-SOTA
- **R75 W2 s59 = single SOTA numeric** (geo 0.4301)
- **r67_w2a / TD3 R67 = paper §IV-C cum_rf SOTA** (cum_rf -0.119)

我 R134 "hidden SOTA", R135 "fresh-SOTA discovery", R136 "strict dominance over R72_w4" 全是**项目已知**的 framework 的 re-derivation. 我没先 audit documentation 就开始 claim novelty, 这是 methodology mistake.

**真正 salvageable**:
1. N=91 Pearson r(geo, cum_rf) = +0.533 (项目没算过的 quantitative statistic)
2. **Degenerate attractor cluster characterisation** — r67_w2a + warm-h_0 都在 (geo≈0.025, cum_rf≈-0.031), discrete cluster 跟 LSTM SOTA cluster (geo≈0.41, cum_rf≈-0.068) 完全分离. **没有 smooth Pareto curve 连接两个 cluster** — 这是 R136 figure 真正的新 contribution.
3. Stale-scoring methodology issue (R57-R69 era cached _summary.json 用 older scoring)

**Lesson**: claim "discovery" 前先 audit project documentation. CLM-0118 + CLM-0131 + CLM-0123 是 authoritative SOTA framework. 任何 metric 新 claim 必须 cite 这些.

**我默认下一步做**：(1) R137 关闭 closed-positive, CLM-0255 写入 post-mortem (已完成). (2) **wind-down**: 这个 session 的 metric-divergence track 该结束了. R86 → R137 共 ~15 rounds, 前 12 个 chain 是 warm-h_0 path (R128 post-mortem), 后 3 个 chain (R134-R136) 是 SOTA-rediscovery (R137 post-mortem 此). 都已 closed honestly. (3) 任何继续都应该 (a) 你告诉我新方向 / (b) 我 audit 现有 R130+ 还有什么 truly novel angle 没挖. 沉默就这么做.

**你想插一脚就说**：(a) 想我继续挖 truly novel angle — 我可以 audit R130 后面其他 session 在跑的 td3_qr_lstm / td3_afe_lstm / td3_warmh0_qr_afe_lstm 等新 agent class 是否产生了新 paper-worthy finding (它们都在试 cum_rf path); (b) 想我 wind-down 把 R136 figure 加 corrected caption 重新 save 一份 — 5 min; (c) 想我整个 R86-R137 chain 写一份 honest "what's actually novel" summary — 30 min, 给 future-session anchor; (d) 你告诉我新方向. 我推荐 (默认) **(2)+(b)+(c)**: 把 R136 figure 加 corrected caption + 写 honest novelty summary, 然后 wind-down 等 PI.
