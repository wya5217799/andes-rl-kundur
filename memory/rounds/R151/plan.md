---
round: R151
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R151 plan — Paper-ready Fig 9 (R139 + R141 consolidation)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续". R141 default next (option b) — merge R139
density panel + R141 algo-breakdown panel into one paper-quality
Fig 9 for Sec.IV-D.
**Parent**: CLM-0264 (R139), CLM-0268 (R141)

## TL;DR

2-panel matplotlib figure:
- Panel A: (cum_rf, geo) scatter, 3 cluster regions shaded, per-algo
  colour, 3 named anchors (R75 W2 s59 / R72_w4 / r67_w2a)
- Panel B: horizontal bar chart per-algo cluster fraction

Output: PNG 200 DPI + vector PDF + provenance JSON. Single figure
captures the session's surviving novel contributions.

Zero ANDES.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | `r151_attractor_figure.py` + run | ~20 min |
| W2 | CLM-0274 + verdict + render | ~15 min |

## 资源冲突 gate

R83-R141 done; WSL free ✅. Read-only ✅.

## 资产保护契约

不动: V4, ckpt, test, R135 / R139 / R141 outputs.

新建:
- `scripts/r151_attractor_figure.py`
- `results/r151_attractor_figure/{fig9.png, fig9.pdf, summary.json}`
- `memory/rounds/R151/{plan.md, verdict.md}`
- `memory/claims/CLM-0274.md`

## Cross-references

- CLM-0264 (R139 bimodal) — Panel A density source
- CLM-0268 (R141 algo breakdown) — Panel B source
- CLM-0118 / CLM-0131 / CLM-0123 — anchor SOTAs annotated
- CLM-0274 (this round)
