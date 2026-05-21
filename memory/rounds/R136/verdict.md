# R136 verdict — r74_w3 strictly dominates R72_w4 (paper SOTA pivot anchor)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (r74_w3 strict dominance over R72_w4 confirmed; paper SOTA pivot ready)
**Type**: synthesis figure + table (integrates R112/R130/R134/R135, zero ANDES)
**Wall**: ~60 min

## TL;DR

R135 discovered r75_baseline as fresh-geo SOTA + r74_w3 as best-of-both.
R136 produces the paper-ready 6-anchor table integrating R135 + R134 +
R130 + R112 findings.

**Key result: r74_w3_lstm_tau0007_warmup20_s54 STRICTLY DOMINATES
R72_w4 SOTA** — fresh geo 0.410 (+5%) AND cum_rf -0.068 (matched).
No metric trade-off. r74_w3 should be the new project SOTA.

r75_baseline trades cum_rf (-10%) for higher geo (+10%) — real
Pareto trade, not strict dominance.

Degenerate cum_rf-optimisers (r67_w2a, warm-h_0) cluster at
geo=0.02-0.03 — completely different basin from LSTM SOTA cluster.

Zero ANDES.

## Methodology

`evaluate_trace` + `compute_global_cum_rf` on 6 anchors:
- r75_baseline (s59) — fresh-geo SOTA candidate
- r74_w3_lstm_tau0007_warmup20_s54 — best-of-both candidate
- R72_w4_lstm_tau001_warmup5_s54 — declared project SOTA
- r67_w2a_td3_combo_tau001 — cum_rf-top per R134, geo-degenerate per R135
- warm-h_0 inference on R72_w4 — R112 inference test
- no_control floor — zero-action reference

3 script-iteration bugfixes (path absolute conversion, ASCII markers,
trace filename pattern with seed suffix).

## Results

| Ckpt | Fresh geo | cum_rf | Role |
|---|---|---|---|
| r75_baseline (s59) | **0.430** | -0.075 | Fresh geo SOTA |
| **r74_w3_lstm_tau0007_warmup20_s54** | **0.410** | **-0.068** | **STRICT DOMINATOR of R72_w4** |
| r72_w4_lstm_tau001_warmup5_s54 | 0.391 | -0.068 | Declared SOTA (no longer best) |
| no_control floor | 0.094 | -0.217 | Zero-action reference |
| r67_w2a_td3_combo_tau001 | 0.028 | -0.031 | Cum_rf-top, geo-degenerate |
| warm-h_0 inference | 0.017 | -0.031 | Catastrophic degenerate |

### Strict dominance: r74_w3 over R72_w4

- geo: 0.410 vs 0.391 — **+5%** (r74_w3 better)
- cum_rf: -0.068 vs -0.068 — **matched** (within numerical noise)
- algorithm: both TD3+LSTM h=64
- hyperparameter differences:
  - tau: 0.0007 (r74_w3) vs 0.001 (R72_w4) — slightly slower target update
  - warmup: 20 (r74_w3) vs 5 (R72_w4) — longer exploration phase
  - seed: 54 (same)

These are minor hyperparameter variations within the R72-R74 LSTM family.
r74_w3 was apparently a "small-perturbation" experiment that the project
ran but didn't promote to SOTA. R135 / R136 retroactively certify it.

### Pareto trade: r75_baseline

- geo: 0.430 vs R72_w4 0.391 — +10%
- cum_rf: -0.075 vs -0.068 — -10% (slightly worse)
- Not strictly dominant but Pareto-noncomparable

### Degenerate cluster

r67_w2a + warm-h_0 occupy:
- geo: 0.017-0.028
- cum_rf: -0.031 (vs LSTM SOTA -0.068)

They're in a completely different basin. The trade-off (LSTM cluster ↔
degenerate cluster) is **discrete** — there's no smooth Pareto curve
between (geo, cum_rf) = (0.41, -0.068) and (0.03, -0.031). Only two
known operating points.

### no_control floor

geo=0.094 (R30 era used 0.104 — small scoring difference). Geo SOTA is
4.6× better than no_control; cum_rf SOTA is 7× better. Both metrics
agree on the basic "policy beats nothing" claim.

## Paper Sec.IV-D recommended narrative

> "Among 91 cached evaluations spanning R57-R75 algorithm and
> hyperparameter sweeps, the project's previously declared SOTA
> (r72_w4_lstm, geo=0.391, cum_rf=-0.068) is **strictly dominated** by
> r74_w3_lstm_tau0007_warmup20_s54 (geo=0.410 [+5%], cum_rf=-0.068
> [matched]). On the joint (geo, cum_rf) Pareto plane, r74_w3 occupies
> the frontier alongside r75_baseline (geo=0.430, cum_rf=-0.075).
> Policies optimising cum_rf alone (r67_w2a, cum_rf=-0.031) collapse to
> a degenerate attractor (geo=0.028), same regime as warm-h_0
> inference. This degenerate cluster is discrete — there is no smooth
> Pareto curve connecting it to the LSTM-policy attractor; the only
> known operating points are the LSTM cluster and the saturation
> cluster."

## Decision

R136 promotes the following paper recommendations:
1. **Replace R72_w4 with r74_w3 as the paper headline policy** (strict dominance)
2. **Report (geo, cum_rf) jointly** for every policy
3. **Acknowledge the discrete attractor structure**: only 2 known regimes
   (LSTM cluster vs degenerate saturation cluster). Continuous Pareto
   curves don't appear to exist in the policy space the project sampled.

## Infrastructure changes

不动: any code, V4, ckpt, test.

新建:
- `scripts/r136_paper_anchor_table.py`
- `results/r136_paper_anchor/{table.md, anchor_scatter.png, .pdf, summary.json}`
- `memory/rounds/R136/{plan.md, verdict.md}`
- `memory/claims/CLM-0254.md`

## Cross-references

- CLM-0250 (R135 fresh-SOTA correction)
- CLM-0238 (R130 per-axis breakdown)
- CLM-0204 (R112 metric divergence)
- CLM-0254 (this round)

## Questions opened (this round)

- (none formal)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** — paper SOTA pivot from R72_w4 → r74_w3 strengthens the
  "plateau ceiling" reframe: 91-round plateau is at geo=0.410+ for
  best-of-both, geo=0.430 for geo-only.

## 给 PI 的话

**这周干了啥**：你说"继续科研, 有问题就优化". R135 我发现 r75_baseline 是 fresh-geo SOTA, r74_w3 是 best-of-both. R136 整合: 6 anchor table + scatter figure 给 paper Sec.IV-D. 包括 r75_baseline / r74_w3 (R135 SOTA candidates), R72_w4 (declared SOTA), r67_w2a (cum_rf-top degenerate), warm-h_0 inference, no_control floor. 3 个 bug 改 (path 转 absolute, ASCII marker, trace filename seed suffix).

**结果（一句话, clean）**: **r74_w3_lstm_tau0007_warmup20_s54 严格 dominates R72_w4 SOTA** — fresh geo 0.410 (+5%) AND cum_rf -0.068 (持平). 完全无 trade-off, paper headline 应该 pivot 从 R72_w4 → r74_w3. r75_baseline geo 更高 (+10%) 但 cum_rf 更差 (-10%), 是 Pareto trade 不是 strict dominance. r67_w2a / warm-h_0 在 (geo 0.02-0.03, cum_rf -0.031) 退化 cluster, 跟 LSTM SOTA cluster (geo 0.41, cum_rf -0.068) 完全 discrete — **没有 smooth Pareto curve**, 只有两个 attractor basin.

**意外**: r74_w3 跟 R72_w4 hyper 差很小 (tau 0.0007 vs 0.001, warmup 20 vs 5), 项目 R74 wave 跑了但没 promote. R72_w4 SOTA 在 R72 期 declared 后, R73/R74/R75 wave 训出更好的 ckpts 但 SOTA-pointer 没 update. R136 retroactively certify r74_w3 是真 SOTA.

**Paper Sec.IV-D 新 narrative**: "91-round sweep 项目 declared SOTA (R72_w4, geo 0.391) 实际被 r74_w3 (geo 0.410 +5%, cum_rf 持平) **strictly dominated**. Pareto frontier 在 (geo 0.41-0.43, cum_rf -0.068 to -0.075). Cum_rf 唯一优化导致 degenerate cluster (geo 0.02-0.03). Discrete attractor structure — 没 smooth Pareto curve."

**我默认下一步做**：(1) R136 关闭 closed-positive, CLM-0254 写入 (已完成). (2) **建议 PI 决定**: 是否 update CONTEXT.md / STATE.md SOTA pointer 从 R72_w4 → r74_w3. R136 已 give 数据, 决定权在 PI. (3) 继续 zero-conflict 离线: 下个 R137 候选 — (a) audit "为什么 r74_w3 没被 promote 在 R74 期" (查 R74 verdict), (b) 跑 r74_w3 ckpt 做更详细 per-axis vs R72_w4 (看是不是 r74_w3 在某个具体 axis 显著优), (c) 把 R135 fresh-score 推广: 跑 R86 / R88 / R104 等 zero-ANDES 离线 forensics 用 r74_w3 而非 R72_w4 (复 valid 我之前 chain 的 finding). 沉默继续干.

**你想插一脚就说**：(a) 想我 R137 audit R74 verdict 看为啥 r74_w3 没 promote — 5 min 读 memory/rounds/R74/; (b) 想我跑 r74_w3 vs R72_w4 详细 per-axis 看具体哪个 axis r74_w3 赢 — 离线 15 min; (c) 想我把 R86 cross-ckpt 用 r74_w3 替换 R72_w4 重跑 R104 grad-ascent (R104 用 R72_w4, 如果 r74_w3 也 universal feasible 则 finding 跨 SOTA 普适) — 离线 20 min; (d) wind-down 等 PI decisions. 我推荐 (默认) **(1)+(2)+(a)+(b)**: 5 min audit R74 verdict + 15 min r74_w3 per-axis comparison, 给 paper Sec.IV-D 数据集合.
