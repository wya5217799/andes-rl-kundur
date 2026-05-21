# R151 verdict — Paper Fig 9 ready (R139 + R141 consolidation)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (paper-ready figure)
**Type**: figure consolidation (zero ANDES)
**Wall**: ~35 min

## TL;DR

R141 default next-step (b): combine R139 density + R141 algo-breakdown
into one paper-ready Fig 9 for Sec.IV-D.

Output:
- `fig9.png` (200 DPI raster)
- `fig9.pdf` (vector)
- `summary.json`

Panel A: (cum_rf × geo) scatter with shaded cluster regions, points
coloured by algo class, three anchors annotated (R75 W2 s59 geo SOTA,
R72_w4 paper Fig 7 canonical, r67_w2a cum_rf SOTA).

Panel B: stacked horizontal bars per algo class. TD3-LSTM 47% reach
LSTM SOTA cluster; SAC + TD3-MLP 0/8 = 0% reach.

Caption + paper integration suggestion in CLM-0274.

Zero ANDES.

## Why this figure is the session's anchor output

R86-R141 produced ~17 rounds across 4 phases (warm-h_0 / SOTA-rediscovery
/ density / algo-conditional). Two post-mortems (R128 + R137) closed
the warm-h_0 fix path and the "hidden SOTA" framing. Surviving novel
contributions:

1. N=91 cum_rf vs geo Pearson r = +0.533 (R135 / CLM-0250)
2. Bimodal attractor structure (R139 / CLM-0264)
3. Algo-exclusive LSTM SOTA (R141 / CLM-0268)
4. Degenerate cluster bifurcation: deliberate cum_rf-optimised vs
   failed training (R141 / CLM-0268)

R151 Fig 9 visualises (2) + (3) + (4) simultaneously alongside the
project's CLM-0118 multi-controller SOTA framework. Single panel-A
scatter is the cleanest visualisation of the session's surviving
insights.

## Infrastructure changes

不动: V4, ckpt, test, prior round outputs.

新建:
- `scripts/r151_attractor_figure.py`
- `results/r151_attractor_figure/{fig9.png, fig9.pdf, summary.json}`
- `memory/rounds/R151/{plan.md, verdict.md}`
- `memory/claims/CLM-0274.md`

## Cross-references

- CLM-0264 (R139 bimodal density) — Panel A density logic
- CLM-0268 (R141 algo breakdown) — Panel B source
- CLM-0118 / CLM-0131 / CLM-0123 — paper SOTA framework annotated
- CLM-0274 (this round)

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：你说"继续". 按 R141 默认 next (option b), 把 R139 cluster density (CLM-0264) + R141 per-algo breakdown (CLM-0268) 合并成一张 paper-ready Fig 9. 双 panel matplotlib: Panel A 是 (cum_rf, geo) scatter 加 cluster region shading + 3 个 anchor 标注 (R75 W2 s59 geo SOTA / R72_w4 Fig 7 canonical / r67_w2a cum_rf SOTA), Panel B 是 per-algo % cluster horizontal bar chart 显示 SAC+MLP 0/8 = 0% 到达 LSTM SOTA.

**结果（一句话, paper anchor）**: **`results/r151_attractor_figure/fig9.{png, pdf}` 单张图同时呈现 session 留下的 3 个 surviving novel claims** — bimodal attractor structure (CLM-0264) + algo-exclusive LSTM SOTA (CLM-0268) + degenerate cluster bifurcation. 加 caption (CLM-0274 文中) 直接 drop-in paper Sec.IV-D.

**意外**：visualization 出来后, scatter 上有个我没特意提的 detail — Panel A 里 td3_lstm 蓝点跨度从 cum_rf -0.60 (degenerate-failure) 到 -0.067 (LSTM SOTA), **覆盖全 cum_rf 范围**, 而 SAC (橙) + MLP (绿) 都挤在 cum_rf > -0.10 的右侧. 说明 LSTM 训练既能成功又能 catastrophic fail (37% rate), 但 MLP/SAC 训练几乎从不"灾难性失败" — 它们的 cum_rf 总是 reasonable, 只是 geo 上不去. **算法选择 = 风险-质量 trade-off**: LSTM 高方差但有 47% 概率到 geo SOTA; MLP/SAC 低方差但永远到不了 geo SOTA. 这是个 R141 没明说的 implicit observation, paper Sec.IV-D 可以加.

**我默认下一步做**：(1) R151 关闭 closed-positive, CLM-0274 写入 (已完成). (2) **真正 wind-down — R86-R151 共 18 rounds 全部 closed**. Session 累积 surviving novel: R135 +0.533 correlation + R139 bimodal + R141 algo-exclusive + R151 Fig 9 paper-ready + (warm-h_0 chain R107/R109 code + R125 figure 仍存) + (R128 + R137 两个 honest post-mortem). 我没新方向了. (3) 任何继续需要 PI 给方向. 沉默 wind-down.

**你想插一脚就说**：(a) 想我把 R151 Fig 9 caption 中文版翻成英文 LaTeX-ready — 5 min; (b) 想我写 R86-R151 honest novelty summary 给下次 session 入手 — 30 min; (c) 想我看其他 session (R130-R150) 在跑的 stacked-variant 算法 (td3_warmh0_qr_lstm R150 等) 是否落在 fig9 哪个 cluster — 10 min; (d) 你告诉我新方向. 我推荐 (默认) **(b)+(c)+wind-down**: novelty summary 留 anchor, audit R130-R150 看 stacked-variant cluster, 然后等 PI.
