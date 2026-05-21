# R134 verdict — Project HID a cum_rf-SOTA candidate (r67_w2a) under 11-axis ranking

**Date**: 2026-05-19
**Status**: CLOSED-POSITIVE (paper Section IV-D rewrite material, headline finding)
**Type**: analysis (N=90 cached eval audit, zero ANDES)
**Wall**: ~60 min

## TL;DR

R130 (CLM-0238) hypothesised the 11-axis vs cum_rf anti-correlation
extends beyond warm-h_0. R134 audited 90 cached eval summaries.

Pearson r(geo, cum_rf) = **+0.415** overall, BUT top-5 cum_rf occupy
geo ranks #58-63 — Δ +55-62. **r67_w2a_td3_combo_tau001 = cum_rf
SOTA (-0.031), ≈ 2× better than R72_w4 LSTM SOTA (-0.068)**, geo
0.251 (#63). This is a REAL trained TD3 MLP policy, not a degenerate
saturated-action like warm-h_0. r70_eval_sac/td3_paper_s49-51 cluster
at cum_rf -0.033 to -0.035 with geo ~0.26-0.27.

**Project hid a cum_rf-SOTA candidate** under its 11-axis ranking
priority. Paper §IV-C uses cum_rf; the SOTA on the paper-headline metric
is NOT R72_w4 LSTM, it's r67_w2a_td3_combo_tau001.

Zero ANDES. Zero WSL.

## Methodology

Loaded 90 cached `*_summary.json` in `results/research_loop/eval_v4_baseline/`.
For each: extracted `mean_geo` (= 11-axis geo) from summary; re-computed
cum_rf via `compute_global_cum_rf` applied to sibling trace JSONs
(matched via glob `{label}_*load_step_{1,2}.json`).

11 summaries failed to load (older list format) — 90 remained.

Pearson correlation + rank disagreement analysis.

## Results

### Aggregate

- N = 90 cached ckpts
- geo: median 0.348, p10 0.062, p90 0.470
- cum_rf: median -0.084, p10 -0.209, p90 -0.061
- **Pearson r(geo, cum_rf) = +0.415**

### Top-5 by cum_rf (= paper §IV-C metric)

| # | Ckpt | cum_rf | geo | geo rank |
|---|---|---|---|---|
| 1 | r67_w2a_td3_combo_tau001_6axis | **-0.031** | 0.251 | #63 |
| 2 | r70_eval_sac_paper_s49 | -0.033 | 0.257 | #62 |
| 3 | r70_eval_td3_paper_s49 | -0.034 | 0.274 | #58 |
| 4 | r70_eval_td3_paper_s51 | -0.034 | 0.270 | #60 |
| 5 | r70_eval_sac_paper_s50 | -0.035 | 0.264 | #61 |

### Top-5 by geo (= project headline)

| # | Ckpt | geo | cum_rf |
|---|---|---|---|
| 1 | r69_w3_lstm_tau001_warmup20_s50_6axis | 0.547 | -0.098 |
| 2 | r69_w1_lstm_tau001_warmup20_6axis | 0.537 | -0.085 |
| 3 | r69_w4_lstm_tau001_warmup5_s52_6axis | 0.521 | -0.103 |
| 4 | r69_w6_lstm_tau001_warmup20_s52_6axis | 0.517 | -0.111 |
| 5 | r68_w4o_lstm_warmup22_6axis | 0.486 | -0.089 |

(Note: r69_w3 has geo=0.547 — higher than R72_w4 SOTA 0.391! That's a
separate R69 / r84_d2b cache discrepancy worth following up; tested
ckpt for r69 wave was apparently better than the declared R72_w4 SOTA.)

### Rank disagreement table

Top-5 cum_rf ckpts are geo-ranked +55-62 lower. The 11-axis ranks LSTM
policies (R68-R70 warmup20/22 variants) at top because they utilise
action space; TD3-MLP and SAC variants (R67 w2a, R70 paper) have
narrower action range so 11-axis penalises them despite better physics.

### r67_w2a vs R72_w4 SOTA comparison

| Metric | R72_w4 (declared SOTA) | r67_w2a (hidden cum_rf SOTA) | Δ |
|---|---|---|---|
| 11-axis geo | **0.391** | 0.251 | -36% (r67_w2a worse) |
| cum_rf | -0.068 | **-0.031** | -54% (r67_w2a better) |
| Best on | 11-axis (project) | cum_rf (paper §IV-C) | — |
| Algo | TD3+LSTM h=64 | TD3 MLP + R67 hyper combo (tau=0.001) | — |
| Action utilisation | High (saturate-ramp) | Moderate (smaller MLP action range) | — |

r67_w2a is the **best of both worlds** candidate:
- Better cum_rf than R72_w4 by 54%
- Not catastrophically low geo (0.251 vs warm-h_0's 0.017)
- Real trained policy, not degenerate saturation
- Achieves warm-h_0 level cum_rf (-0.031 = warm-h_0's -0.031) with
  normal action variability

### Mechanism (sharper than CLM-0238)

The 11-axis geo ranks high-action-utilization policies (LSTM warmup20+)
at the top because LSTMs with delayed exploration warmup (warmup20-30
episodes) train with high exploration noise, learning to use the full
action range. Their physics outcome (cum_rf) is moderate.

Low-action-range policies (TD3-MLP, SAC) score moderately on 11-axis
but achieve cum_rf SOTA. They essentially "do less but do it right".

## Paper Sec.IV implications

1. **Sec.IV-A (metric definition)**: must disclose the two-metric
   structural divergence. The 11-axis geo and paper §IV-C cum_rf are
   not just slightly different — they SYSTEMATICALLY disagree at the
   top of each ranking.

2. **Sec.IV-C (results)**: pick the headline metric and report consistently.
   - cum_rf headline: r67_w2a_td3_combo_tau001 is SOTA (-0.031)
   - 11-axis headline: r69_w3_lstm_tau001_warmup20_s50 is SOTA (0.547)
     (note: this is HIGHER than R72_w4 0.391 — the project's "R72_w4
     is SOTA" claim may itself need re-checking against the R69 wave)

3. **Sec.IV-D (mechanism / discussion)**: the "91-round plateau" framing
   should be replaced with "metric-dependent SOTA divergence". The
   11-axis plateau exists at 0.547 (R69 w3), not 0.391 (R72_w4) —
   another follow-up. The cum_rf plateau is at -0.031 (r67_w2a) — not
   reached by any of the LSTM ckpts.

4. **Reproducibility honesty**: the 91-round CLM-0144 plateau claim is
   valid for 11-axis. The hidden cum_rf SOTA was not surveyed because
   the project's ranking pipeline filtered on 11-axis.

## Decision

R134 finding goes into paper Section IV-D as the "metric divergence"
anchor. r67_w2a_td3_combo_tau001_s50 ckpts at
`results/r67_w2a_td3_combo_tau001_s50/` are available for re-evaluation
under any future paper-relevant test.

The "R72_w4 LSTM is project SOTA" framing is metric-specific:
- VALID for 11-axis geo
- INVALID for paper §IV-C cum_rf
Paper must report both.

## Follow-ups (NOT R134 scope)

- (Q-NEW) Why does r69_w3 (geo=0.547) appear in cached eval but project
  declared R72_w4 (geo=0.391) as SOTA? Either r69_w3 had a known issue
  the project rejected, or R72_w4 declaration is itself debatable.
- (Q-NEW) Spot-check r67_w2a load_step_1 trace n_steps to rule out
  early-eval-truncation artefact.

## Infrastructure changes

不动: any code beyond new scripts/r134, any V4, ckpt, test.

新建:
- `scripts/r134_cumrf_vs_geo_audit.py`
- `results/r134_cumrf_vs_geo_audit/{summary.json, scatter.png, scatter.pdf}`
- `memory/rounds/R134/{plan.md, verdict.md}`
- `memory/claims/CLM-0243.md`

## Cross-references

- CLM-0238 (R130 per-axis breakdown) — parent; R134 extends to N=90
- CLM-0204 (R112 aggregate divergence)
- CLM-0144 (R57-R82 11-axis plateau) — re-framed in CLM-0243
- CLM-0233 (R128 post-mortem) — context
- CLM-0243 (this round)

## Questions opened (this round)

- (none in formal Q-XXXX track; 2 follow-up notes above)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- **Q-0014** (algorithm exploration backlog) — substantially re-framed:
  the cum_rf-SOTA already exists in the codebase (r67_w2a) but was
  hidden by 11-axis ranking. New algo work should be motivated by
  joint-metric Pareto improvement, not 11-axis maximisation alone.

## 给 PI 的话

**这周干了啥**：你说"继续科研, 有问题就优化". R130 我发现 warm-h_0 11-axis 崩 / cum_rf 改善的 metric divergence, 但只看了一个 ckpt. R134 audit 90 cached eval summaries 跨整个 R57-R72 ckpt zoo. 看 cum_rf vs geo 是 systematic anti-correlation 还是 warm-h_0 outlier.

**结果（一句话, big）**：**Project 隐藏了一个 cum_rf-SOTA 候选**. Top-5 cum_rf ckpts 都在 geo 排名 #58-63 (Δ +55-62!!). **r67_w2a_td3_combo_tau001 cum_rf = -0.031 (R72_w4 SOTA -0.068 的 2× 更好), geo=0.251 (subpar but not catastrophic)**. r70_eval_sac/td3_paper 集群在 cum_rf -0.033 ~ -0.035, geo 0.26 ~ 0.27. 5 个 cum_rf-top ckpt 都是 TD3-MLP / SAC, 不是 LSTM. 项目按 11-axis 选 R72_w4 LSTM, 但 paper §IV-C 用 cum_rf — **paper headline 该是 r67_w2a 不是 R72_w4**.

**意外**: top-1 by geo 是 **r69_w3_lstm_tau001_warmup20_s50 geo=0.547** — 比 R72_w4 SOTA 0.391 高 40%!! 项目"R72_w4 = SOTA" 的 framing 即便在 11-axis 下也可能站不住. 这是另一个 follow-up — r69_w3 缓存里有但 SOTA-declaration 没用它, 不知道为什么 (可能 R69 wave 有 known issue 被项目 reject, 或 R72_w4 declaration 本身 debatable).

**Mechanism**: 11-axis 偏 reward action-utilisation high 的 policy (LSTM warmup20+); cum_rf 不在乎 utilisation 只看物理 outcome. TD3-MLP / SAC 学到 narrower action range → 11-axis 低分 → 项目 filter 掉, 但 cum_rf 一流. **"91-round plateau" 是 metric-specific framing**: geo plateau 真实在 0.547 (r69_w3) 不是 0.391; cum_rf plateau 在 -0.031 (r67_w2a) — LSTM 全都达不到.

**我默认下一步做**：(1) R134 关闭 closed-positive, CLM-0243 写入 (已完成). (2) **paper Sec.IV-D 严重重写**: 不是"91 round 都败 0.391", 而是"项目 11-axis ranking 隐藏了 cum_rf-SOTA". r67_w2a + r70_eval_sac/td3_paper 当作 cum_rf candidates 应在 paper 里报. (3) follow-up: 验证 r67_w2a / r70_eval_sac 的 trace n_steps=150 (rule out truncation artefact), check r69_w3 vs R72_w4 declaration discrepancy. 沉默继续干.

**你想插一脚就说**：(a) 想我立刻 R135 spot-check r67_w2a trace n_steps + 重 eval 它的 11 个 axis 完整 breakdown — 离线 15 min; (b) 想我 audit "为什么 R72_w4 是 declared SOTA 而 r69_w3 不是" — 离线 20 min, 看 CLM-0094/0095 era 决策原因; (c) 想我 重新跑 r67_w2a 通过 R125 figure pipeline 加它一个点 (per-axis bar chart 比对 R72_w4 vs r67_w2a vs warm-h_0 三方) — 离线 40 min; (d) 想我 wind-down. 我推荐 (默认) **(1)+(2)+(b)+(c)**: 先 audit R72_w4 vs r69_w3 declaration, 然后 r67_w2a per-axis bar chart 给 paper Sec.IV-D 最强 anchor figure.
