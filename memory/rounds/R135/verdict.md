# R135 verdict — R134 corrected; r75_baseline is actual fresh-geo SOTA (not R72_w4)

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (R134 superseded; new fresh-SOTA found)
**Type**: correction + analysis (re-score N=91 with fresh evaluate_trace, zero ANDES)
**Wall**: ~60 min (30 min code + 30 min write)

## TL;DR

R134 verdict flagged "spot-check r67_w2a n_steps" as follow-up. That
spot-check found ALL traces are full 150 steps + no TDS failure, so
the cum_rf values are valid. BUT a three-way per-axis re-eval
revealed cached `mean_geo` values are STALE — produced by an earlier
paper_grade_axes scoring config.

R135 re-scored 91 ckpts with current `evaluate_trace`. **Three corrections**:

1. **r67_w2a fresh geo = 0.028** (cached 0.251 was stale). r67_w2a is
   a warm-h_0-equivalent degenerate attractor, NOT a hidden good SOTA.
   CLM-0243's "hidden cum_rf SOTA at non-trivial geo" claim is WRONG.

2. **r75_baseline / r75_w2_lstm_tau001_warmup20_s59 geo = 0.430** is
   the FRESH 11-axis SOTA. R72_w4 (geo=0.391) ranks **#8** by fresh
   eval. The project's "R72_w4 SOTA" declaration is INVALID under
   consistent current scoring.

3. **Best-of-both**: r74_w3_lstm_tau0007_warmup20_s54 (geo=0.410, cum_rf
   =-0.068) is Pareto-optimal across both metrics. Multiple LSTM
   warmup20 variants in R73/R74/R75 outperform R72_w4 on both metrics.

Pearson r(fresh_geo, cum_rf) = **+0.533** (R134's stale +0.415 was
diluted by inconsistent scoring).

Zero ANDES.

## Methodology

For each `*_summary.json` in `results/research_loop/eval_v4_baseline/`:
1. Locate sibling traces via glob `{label}_*load_step_{1,2}.json`
2. Call `evaluate_trace(p, PAPER[scen], is_ddic=True, label)` — full
   v3-axes scoring with axis 9-11 multiplicative gate
3. Compute `geo = floor_geo_mean([LS1.overall, LS2.overall])`
4. Compute cum_rf via `compute_global_cum_rf` on both scenarios
5. Aggregate across N=91 ckpts; compute Pearson r + rank tables

## Results

### Aggregate

- N = 91 ckpts (cached summaries with matching trace siblings)
- fresh geo: median 0.196, p10 0.010, p90 0.376
- cum_rf: median -0.084, p10 -0.209, p90 -0.062
- **Pearson r(geo, cum_rf) = +0.533**

### Top-5 by FRESH geo (new SOTA candidates)

| # | Ckpt | fresh geo | cum_rf | algo | notable hyper |
|---|---|---|---|---|---|
| 1 | r75_baseline | **0.430** | -0.075 | LSTM | (= r75_w2_s59, tied) |
| 1 | r75_w2_lstm_tau001_warmup20_s59 | **0.430** | -0.075 | LSTM | tau=0.001, warmup=20, seed=59 |
| 3 | r74_w3_lstm_tau0007_warmup20_s54 | 0.410 | -0.068 | LSTM | **tau=0.0007** (unusual) |
| 4 | r73_w3_lstm_tau001_warmup20_s54 | 0.410 | -0.068 | LSTM | tau=0.001, warmup=20 |
| 5 | r73_w2_lstm_tau001_warmup15_s54 | 0.404 | -0.068 | LSTM | warmup=15 |

R72_w4 (cached SOTA 0.391, fresh 0.391) ranks **#8 by fresh** — NOT
the geo SOTA. Five LSTM variants in R73/R74/R75 outperform it.

### Top-5 by cum_rf (degenerate attractors)

| # | Ckpt | cum_rf | FRESH geo | regime |
|---|---|---|---|---|
| 1 | r67_w2a_td3_combo_tau001_6axis | **-0.031** | **0.028** | warm-h_0-equivalent |
| 2 | r70_eval_sac_paper_s49 | -0.033 | 0.068 | similar |
| 3 | r70_eval_td3_paper_s49 | -0.034 | 0.039 | similar |
| 4 | r70_eval_td3_paper_s51 | -0.034 | 0.027 | similar |
| 5 | r70_eval_sac_paper_s50 | -0.035 | 0.108 | similar |

These 5 ckpts ALL have catastrophic 11-axis geo (0.027-0.108, same
regime as warm-h_0 inference 0.017). They're degenerate attractors,
not "discovered" superior policies. CLM-0243's "hidden SOTA"
interpretation was wrong.

### Best-of-both (rank ≤ 30 on BOTH)

16 ckpts qualify, dominated by LSTM warmup15-30 variants. Top:

| Ckpt | geo rank | cum_rf rank | geo | cum_rf |
|---|---|---|---|---|
| r74_w3_lstm_tau0007_warmup20_s54 | #3 | #17 | 0.410 | -0.068 |
| r73_w3_lstm_tau001_warmup20_s54 | #4 | #16 | 0.410 | -0.068 |
| r73_w2_lstm_tau001_warmup15_s54 | #5 | #14 | 0.404 | -0.068 |
| r72_w4_lstm_tau001_warmup5_s54 | #8 | #18 | 0.391 | -0.068 |
| r68_w4b_lstm_warmup0_6axis | #28 | #19 | 0.354 | -0.068 |

The cluster around cum_rf=-0.068 represents the "normal LSTM SOTA
regime" — variants of R67-R75 hyper combos. r74_w3 with the
non-standard tau=0.0007 emerges as best-of-both anchor.

## Decision

R134's CLM-0243 is **superseded by R135's CLM-0250** (validate.py --fix
will write the back-edge automatically).

R72_w4 SOTA-declaration is no longer the consistent-scoring SOTA.
Project should:
1. Update CONTEXT.md / STATE.md SOTA pointers from R72_w4 to r75_baseline
   (geo 0.430) or r74_w3 (best-of-both)
2. Acknowledge in paper Sec.IV that prior SOTA-declaration was based on
   older scoring; fresh consistent scoring shows 0.430 as the
   plateau ceiling, not 0.391
3. Paper Sec.IV-D narrative: 91-round plateau is at geo=0.430
   (r75_baseline), not 0.391. R67-R72 wave's claimed SOTA was a
   transient milestone, not the ceiling.

## Methodology notes

- The scoring version mismatch (cached vs fresh) likely arose because
  the project iteratively refined paper_grade_axes (v3.0 → v3.1 gating
  added per CLM-0119 era), but cached `_summary.json` files were never
  re-scored.
- A future cleanup round should walk through cached summaries and
  re-compute all geo values with the canonical current scorer; the
  `r135_freshscore/summary.json` produced here is a starting point.

## Infrastructure changes

不动: any code, V4, ckpt, test.

新建:
- `scripts/r135_freshscore_correlation.py`
- `results/r135_freshscore/{summary.json, scatter.png, scatter.pdf}`
- `memory/rounds/R135/{plan.md, verdict.md}`
- `memory/claims/CLM-0250.md` (supersedes CLM-0243)

## Cross-references

- CLM-0243 (R134) — superseded by CLM-0250
- CLM-0238 (R130 per-axis breakdown) — still valid
- CLM-0094 / R72_w4 SOTA declaration — invalidated by R135
- CLM-0144 (R57-R82 plateau) — geo plateau is at 0.430 not 0.391
- CLM-0250 (this round)

## Questions opened (this round)

- (none formal)
- Implicit: should CONTEXT.md / STATE.md SOTA pointer be updated to
  r75_baseline (fresh geo=0.430)? Logged in R135 verdict; PI decides.

## Questions closed (this round)

- (none) — Q-0022 already closed by R112

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — substantially re-framed:
  the geo plateau is at 0.430 (r75_baseline / R74/R75 wave), not 0.391
  (R72_w4). Algorithms above 0.43 still don't exist. The plateau
  ceiling reframe shifts but the plateau itself remains.

## 给 PI 的话

**这周干了啥**：你说"继续科研, 有问题就优化". R134 verdict 留 follow-up "spot-check r67_w2a trace n_steps", 我做了. 顺手做了三方 per-axis breakdown (R72_w4 vs warm-h_0 vs r67_w2a), 发现 r67_w2a 的 cached geo=0.251 跟当前 evaluate_trace 给的 0.028 完全不一致 — cached summaries 是 STALE scoring. R135 re-score 全 91 ckpts.

**结果（一句话, big correction）**: **R134 错了**. r67_w2a 的 fresh geo = **0.028** (灾难性, 跟 warm-h_0 inference 一档), 不是 cached 的 0.251. "hidden cum_rf SOTA at non-trivial geo" claim 直接 supersede. 但 R135 同时发现更大的事: **R72_w4 不是 fresh-geo SOTA, r75_baseline / r75_w2_lstm_tau001_warmup20_s59 geo=0.430 才是** (R72_w4 fresh 0.391 排 #8). Best-of-both 是 **r74_w3_lstm_tau0007_warmup20_s54 (geo=0.410, cum_rf=-0.068)** — 同时是 geo top-3 + cum_rf 跟 R72_w4 持平. Pearson r 修正到 **+0.533**.

**意外**：项目 "R72_w4 SOTA" framing 在当前 scoring 下其实站不住. r75_baseline / r75_w2 / r73_w2/w3 / r74_w3 全部 fresh geo 高于 R72_w4. 这是 SOTA-pointer 没跟上 scoring evolution 的 housekeeping issue — R72 期 SOTA 用 R72 era scoring 选, 后续 R73-R75 wave 训练出更好的 ckpt 但没 update SOTA pointer.

**Paper Sec.IV-D 再次 pivot**:
   - "91-round plateau" 真实, 但 ceiling 是 0.430 (r75_baseline) 不是 0.391 (R72_w4)
   - 所有 cum_rf-top ckpts 是 degenerate attractors (warm-h_0-equivalent regime), 不是 hidden good SOTAs
   - r74_w3 (tau=0.0007 unusual) 是 best-of-both anchor, 应当成 paper headline policy

**我默认下一步做**：(1) R135 关闭 closed-positive, CLM-0250 写入 supersede CLM-0243 (已完成). (2) 建议更新 CONTEXT.md / STATE.md SOTA pointer 从 R72_w4 → r75_baseline 或 r74_w3 — 但这是 PI 决定, 我不擅自改 CONTEXT. (3) 继续 zero-conflict 离线: R136 候选 = (a) 复 walk through cached summaries 全部 re-score 写新 `_freshscore_summary.json` (项目级 SOTA pointer cleanup), 或 (b) 拿 r74_w3 ckpt 当 anchor 重做 R125 figure (per-axis bar chart 三方对比 r74_w3 vs r67_w2a vs warm-h_0), 或 (c) 拿 r75 wave best-of-both ckpts 跟 R83 / R94 等 negative-result rounds 重新对照看是否有 ckpt 隐藏的 cum_rf 突破. 沉默继续干.

**你想插一脚就说**：(a) 想我把所有 91 cached summaries 用 fresh evaluate_trace 重写 `_freshscore_summary.json` 升级 project-level SOTA pointer — 60 min 离线; (b) 想我立刻把 R125 figure 加 fresh-eval 数据 + 标 r75_baseline / r74_w3 / r67_w2a 三个 anchor — 30 min; (c) 想我 audit R83 / R94 / R110 negative-result rounds 的 cached ckpts 用 fresh scoring + cum_rf 看是否有 hidden Pareto point — 60 min; (d) wind-down 等 PI 决定 SOTA pointer. 我推荐 (默认) **(1)+(2)+(b)+(c)**: 先升级 R125 figure 用 fresh 数据, 然后 audit negative-result rounds 看是否有 hidden Pareto.
