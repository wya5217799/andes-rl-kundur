---
round: R134
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R134 plan — cum_rf vs 11-axis geo audit across N=90 cached ckpts

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续科研, 有问题就优化". R130 (CLM-0238) found warm-h_0 has
anti-correlated cum_rf vs geo. R134 tests: systematic or warm-h_0 outlier?
If systematic, project may have HIDDEN SOTAs by cum_rf metric.
**Parent**: CLM-0238 (R130), CLM-0204 (R112), CLM-0144 (R57-R82 plateau)

## TL;DR

Mine all `*_summary.json` in `results/research_loop/eval_v4_baseline/`
(N=90 after deduplication). Re-compute cum_rf from sibling trace JSONs
via `compute_global_cum_rf`. Pearson correlation + rank disagreement.

Result: **systematic anti-correlation at the top**. Pearson r=+0.415
overall (mildly positive), but top-5 by cum_rf have geo ranks #58-63 /
90 (Δ +55-62). **r67_w2a_td3_combo_tau001 = cum_rf SOTA (-0.031) ≈
2× better than R72_w4 LSTM SOTA (-0.068)** but has geo=0.251 (filed as
"subpar"). r70_eval_sac/td3_paper cluster similar.

R72_w4 SOTA is geo-SOTA, NOT cum_rf-SOTA. Paper §IV-C metric makes
r67_w2a the headline candidate.

Zero ANDES. Zero WSL.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | `r134_cumrf_vs_geo_audit.py` + glob-based trace matching + run | ~30 min (with 2 bugfixes) |
| W2 | Verdict + CLM-0243 + render | ~30 min |

Total wall ~60 min.

## 资源冲突 gate

R83-R130 all closed; WSL free; cached read-only ✅

## 资产保护契约

不动: V4 / V4Config / paper_grade_axes / agents/ / R57+ ckpt /
scripts/train.py / any test.

新建:
- `scripts/r134_cumrf_vs_geo_audit.py`
- `results/r134_cumrf_vs_geo_audit/{summary.json, scatter.png, scatter.pdf}`
- `memory/rounds/R134/{plan.md, verdict.md}`
- `memory/claims/CLM-0243.md`

## Cross-references

- CLM-0238 (R130 per-axis breakdown) — parent
- CLM-0204 (R112 metric divergence aggregate)
- CLM-0144 (R57-R82 plateau on 11-axis) — re-framed in CLM-0243
- CLM-0243 (this round)
