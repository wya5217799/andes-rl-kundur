# R252 verdict — Classical baseline DUAL-METRIC AUDIT: droop k=10 beats RL on cum_rf 47%

**Date**: 2026-05-20
**Status**: CLOSED-POSITIVE — CLM-0186 corrected (parallel CLM-0430 pattern)
**Type**: research (analysis-only, no new training)
**Wall**: ~15 min (read existing data + write CLM/verdict/memo update)

## TL;DR

Audited R85 classical-baseline data through dual-metric lens.
**CLM-0186's "RL beats droop 2.1×" was 11-axis-only**; on paper's
cum_rf metric, **droop k=10 (cum_rf=-0.037) BEATS RL SOTA
(cum_rf=-0.069) by 47%**. No controller Pareto-dominates. Wrote
CLM-0445 superseding CLM-0186.

Used new infrastructure end-to-end:
- `round_preflight.py` caught CLM-0445 forward-citation BEFORE
  launch → reserved CLM-0445 first via `reserve_claim.py`.
- `baselines.py` surfaced R85 as `dual?=no` (didn't auto-detect the
  nested envelope) → direct JSON read got the data.
- This is a known limitation; `baselines.py` `--missing-cum-rf` flag
  is a worthwhile follow-up (noted in CLM-0445 cross-references).

## Methodology

No training. Pure analysis of pre-existing R85 data + cross-tab
against measured RL cum_rf anchors (R201/R72_w4/R239 via CLM-0440).

```bash
python memory/tools/baselines.py --filter "r201|r72_w4|r239" --sort cum_rf
python -c "import json; ..." # direct read of R85 droop_all nested array
```

## Key results

### Droop k-sweep dual-metric (R85 data, NEWLY AUDITED)

| k | geo | cum_rf | best on |
|---|-----|--------|---------|
| 0.5  | 0.016 | -0.121 | (worst both) |
| 1.0  | 0.097 | -0.090 | — |
| **2.0** | **0.197** | -0.064 | **geo** (CLM-0186 cited this) |
| 5.0  | 0.194 | -0.041 | — |
| **10.0** | 0.179 | **-0.037** | **cum_rf** |
| 20.0 | 0.173 | -0.039 | — |
| 50.0 | 0.173 | -0.040 | — |

Geo-best (k=2.0) and cum_rf-best (k=10) are **different controllers**.

### Classical vs RL SOTA Pareto frontier

| Controller | geo (11-axis) | cum_rf (paper) |
|------------|---------------|----------------|
| no-control | 0.104 | (unmeasured here) |
| Droop k=2.0 | 0.197 | -0.064 |
| **Droop k=10** | 0.179 | **-0.037** ← Pareto front cum_rf |
| R72_w4 scalar full | 0.391 | -0.068 |
| **R201 hreg SOTA** | **0.415** ← Pareto front geo | -0.069 |
| R239 scalar+only-phi_abs | 0.395 | -0.069 |

**No controller dominates on both metrics**. RL = high-transient-
quality + medium-sync; droop k≥5 = low-transient-quality + high-sync.

## Pre-registered outcomes (from R252 plan)

| Comparison | predicted | actual | matched? |
|-----------|-----------|--------|----------|
| Droop best vs R201 SOTA on geo | RL ~2.1× | R201/droop = 0.415/0.197 = 2.1× | ✅ |
| Droop best vs RL on cum_rf | droop 6-8% better | droop k=10 47% better | ⚠️ much larger than predicted |
| Droop k-sweep monotonicity on cum_rf | bowl shape, min ~k=5 | bowl shape, min at k=10 | ✅ shape; slightly higher k than expected |

**The cum_rf gap is bigger than I predicted in plan** (47% vs 6-8%).
The geo-best k=2.0 has cum_rf much closer to RL (-0.064 vs -0.069);
the cum_rf-best k=10 pulls way ahead. **Different droop k optimises
different metric** — a finding the original plan didn't pre-register.

## Why CLM-0186 missed this

Identical root cause to CLM-0430: the dual-metric data was in
R85's summary JSON, but the verdict cited only geo. CLM-0186 was
authored citing the metric RL was tuned for. Once audited against
the paper's own metric, the conclusion inverts on one of two axes.

## Updates to paper draft

`docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md` gets a
new "Classical vs RL dual-metric Pareto frontier" panel parallel
to the existing "paper Eq.14 dual-metric divergence" section.
Both panels share the same methodological lesson: project's
11-axis ranker and paper's cum_rf measure different quality axes;
report both, don't pick one.

## Implication for "训练更好的agent" objective

If goal is to dominate cum_rf, **droop k=10 is currently best**,
NOT R201. RL's cum_rf plateau (R72/R201/R239/R174 all cluster
-0.068 to -0.070) suggests an unexplored direction: RL trained with
cum_rf directly as reward (or hybrid RL+droop architecture) might
Pareto-dominate. **This is a paper 7th contribution candidate**:
"RL controllers are systematically sub-optimal on the paper's own
reward metric; a cum_rf-direct training objective is the missing
piece."

## Questions opened (this round)

- Q-NNNN: Would training RL with cum_rf-direct reward (instead of
  per-step paper Eq.14) Pareto-dominate droop k=10? (R253+ candidate)
- Q-NNNN: Does the cum_rf divergence at high k arise from droop
  controller having SLOWER transient (allowing time-integrated
  deviation to smooth out the spikes that hurt 11-axis settling)?
  Phase-portrait analysis would resolve mechanism.

## Questions closed (this round)

- (none — analysis-only round, no Q-NNNN was tracking this)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这周干了啥**：用 dual-metric framework (CLM-0430) 重审 CLM-0186
"RL beats droop 2.1×" 这个 paper Sec.IV-D contribution 1 headline.
R85 数据其实早就有 cum_rf, 只是当时只 cite geo. 顺便 dogfood 刚写的
`round_preflight.py` 工具 (catch 了 CLM-0445 forward-citation).

**结果（一句话）**：CLM-0186 11-axis 上 RL 2.1× droop ✅, 但 **paper
cum_rf 上 droop k=10 反过来 47% beat RL SOTA**. **Pareto frontier**:
没 controller 在两 metric 都赢. CLM-0445 supersede CLM-0186.

**意外**：
1. **cum_rf gap 比预期大** (47% 不是 6-8%, plan 估错了). 主因: geo-best
   droop (k=2.0) 跟 RL 在 cum_rf 上接近 (-0.064 vs -0.069), 但 cum_rf-
   best droop 在 k=10 (cum_rf=-0.037), 拉开极大.
2. **Geo-best 跟 cum_rf-best 是不同 droop** (k=2.0 vs k=10). "Best
   droop" 是 metric-dependent. 这本身也是 paper-worthy finding (RL-vs-
   classical comparison 在 hyperparameter-tune-by-metric 上的方法学陷阱).
3. **RL cum_rf plateau 极平** (R72/R201/R239/R174 = -0.068 to -0.070,
   spread 3%). 即使 hreg SOTA 也突破不了. 暗示 RL training 的 implicit
   reward 不在 optimize cum_rf — paper Eq.14 r_f 仅 per-step penalty,
   不积分.

**我默认下一步做**：
1. **不再继续 R252-style audit**: paper Sec.IV-D contribution 1 现已
   dual-metric. Contributions 5 (paper-Eq.14) + 1 (RL-vs-classical)
   都 audit 完, 整 Sec.IV-D 现 honest dual-metric.
2. **R253 候选** (新研究方向): cum_rf-direct RL training. 改 reward
   formula 把 cumulative inter-agent freq deviation 作 episodic
   reward, 看能否 Pareto-dominate droop k=10. **需 env 改动** (新
   round + 文档化 per CLAUDE.md). Codex-level engineering effort.
3. **`baselines.py` follow-up**: 加 `--missing-cum-rf` flag 帮发现
   R85-style 旧 round 缺 canonical envelope; 加 nested-envelope adapter
   for `r85_classical_baseline_summary.json` 类 custom structure.
4. **`dual_metric_lint.py` 扩展**: 加 `classical-baseline-comparison`
   tag 触发. 这次 audit 我 manually caught, 但 lint 应该自动 surface.

**你想插一脚就说**：CLM-0445 + R252 verdict 是 session 第 14 个 CLM,
完成两条 dual-metric 平行修正 (paper Eq.14 + RL-vs-classical). Paper
Sec.IV-D 现 ready for draft with honest dual-metric panels throughout.
如果你 OK 这框架, 我推荐进 paper draft (现有数据足够). 如果觉得 R253
cum_rf-direct RL 是高价值新方向, 我现在 design plan. 默认我等 wakeup.

## Cross-references

- R85 classical baseline (CLM-0186 — superseded)
- CLM-0430 (paper Eq.14 dual-metric — parallel pattern)
- CLM-0440 (R72_w4 cum_rf anchor)
- CLM-0445 (this round's superseding claim)
- `docs/paper_drafts/sec_iv_d_paper_eq14_gauge_invariance.md`
- `memory/tools/round_preflight.py` (dogfooded this round)
- `memory/tools/baselines.py` (revealed limitation; follow-up patch)
