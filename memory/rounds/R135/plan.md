---
round: R135
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R135 plan — Fresh re-score correction of R134 + r75 SOTA discovery

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续科研, 有问题就优化". R134 verdict's "spot-check r67_w2a"
followup turned up cached-summary STALE-scoring issue. R135 = fresh
re-score correction.
**Parent**: CLM-0243 (R134), CLM-0238 (R130)

## TL;DR

Re-score all 91 cached ckpts via current `evaluate_trace` (rather than
stale `_summary.json mean_geo` field). Surprise findings:

1. r67_w2a's cached geo=0.251 was STALE — fresh re-eval = **0.028**
   (catastrophic, warm-h_0-equivalent regime). R134's "hidden SOTA"
   claim was wrong.
2. Pearson r corrected to **+0.533** (R134 +0.415 was diluted by
   inconsistent scoring).
3. **r75_baseline / r75_w2 geo=0.430** is the FRESH 11-axis SOTA — NOT
   R72_w4 (geo=0.391, fresh rank #8).
4. Best-of-both: **r74_w3_lstm_tau0007_warmup20_s54** (geo=0.410,
   cum_rf=-0.068, Pareto-optimal).

Zero ANDES.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | `r135_freshscore_correlation.py` (1 bugfix on floor_geo_mean), run | ~30 min |
| W2 | CLM-0250 (correction supersede R134) + verdict + render | ~30 min |

## 资源冲突 gate

R83-R134 done; WSL free; read-only ✅

## 资产保护契约

不动: any code, V4, ckpt, test.

新建:
- `scripts/r135_freshscore_correlation.py`
- `results/r135_freshscore/{summary.json, scatter.png, scatter.pdf}`
- `memory/rounds/R135/{plan.md, verdict.md}`
- `memory/claims/CLM-0250.md` (supersedes CLM-0243)

## Cross-references

- CLM-0243 (R134) — superseded by CLM-0250
- CLM-0238 (R130 per-axis breakdown) — still valid (uses fresh evaluate_trace)
- CLM-0204 (R112 metric divergence aggregate)
- CLM-0094 (cached R72_w4 SOTA declaration)
- CLM-0250 (this round)
