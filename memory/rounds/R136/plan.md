---
round: R136
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R136 plan — Paper-anchor 6-ckpt table + scatter figure

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续科研, 有问题就优化". R135 found r75_baseline geo=0.430
fresh-SOTA + r74_w3 best-of-both. R136 produces paper-ready table +
figure for Sec.IV-D, integrating R135 + R134 + R130 + R112 findings.
**Parent**: CLM-0250 (R135), CLM-0238 (R130), CLM-0204 (R112)

## TL;DR

Score 6 representative anchors with fresh evaluate_trace + cum_rf:
r75_baseline, r74_w3 (best-of-both), R72_w4 (declared SOTA),
no_control, r67_w2a (cum_rf-top degenerate), warm-h_0 inference.

Result: **r74_w3 strictly dominates R72_w4** (geo +5%, cum_rf
matched). r75_baseline has higher geo (+10%) but worse cum_rf (-10%)
— a Pareto trade. Degenerate cum_rf-optimisers cluster at geo 0.02-0.03.

Zero ANDES.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | `r136_paper_anchor_table.py` + 3 bugfixes (path, marker, trace pattern) + run | ~35 min |
| W2 | CLM-0254 + verdict + render | ~25 min |

## 资源冲突 gate

R83-R135 done; WSL free ✅
Read-only cached traces ✅

## 资产保护契约

不动: any code, V4, ckpt, test.

新建:
- `scripts/r136_paper_anchor_table.py`
- `results/r136_paper_anchor/{table.md, anchor_scatter.png, .pdf, summary.json}`
- `memory/rounds/R136/{plan.md, verdict.md}`
- `memory/claims/CLM-0254.md`

## Cross-references

- CLM-0250 (R135 fresh-SOTA correction) — parent
- CLM-0238 (R130 per-axis breakdown)
- CLM-0204 (R112 metric divergence)
- CLM-0254 (this round)
