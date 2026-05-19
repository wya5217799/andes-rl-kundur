---
round: R125
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R125 plan — Paper-quality summary figure (R104 + R117 integration)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "一直干活". 11+ CLM mechanism chain accumulated through R86-R117
needs a single anchor figure for paper Sec.IV-D. CLM-0188 (warm-h_0 universal)
+ CLM-0217 (obs hard ceiling universal) fit on one scatter.
**Parent**: CLM-0188, CLM-0217

## TL;DR

Load r104 + r117 summary.json; per-ckpt scatter (x = obs-only max %,
y = h-warm median %); paper-quality matplotlib output (PNG 200 DPI +
vector PDF + raw CSV). All 9 ckpts cluster upper-left, median
asymmetry +67.7 pp, no overlap between two path distributions.

Zero ANDES. Zero WSL.

## Wave 顺序

| Wave | 内容 | Wall |
|---|---|---|
| **W1** | `r125_step0_barrier_figure.py` + run | ~30 min |
| **W2** | Verdict + CLM-0225 + render | ~15 min |

Total wall ~45 min.

## 资源冲突 gate

R83 / R94 / R102 / R110 etc.: zero WSL ✅
Inputs: r104 + r117 summary.json (read-only) ✅
Output: `results/r125_step0_barrier_figure/` (new namespace) ✅

## 资产保护契约

不动: any code, V4, ckpt, test, other rounds' data.

新建:
- `scripts/r125_step0_barrier_figure.py`
- `results/r125_step0_barrier_figure/{barrier.png, barrier.pdf,
  barrier_data.csv, summary.json}`
- `memory/rounds/R125/{plan.md, verdict.md}`
- `memory/claims/CLM-0225.md`

## Cross-references

- CLM-0188 (R104 warm-h_0 universal) — Y-axis source
- CLM-0217 (R117 obs ascent universal) — X-axis source
- CLM-0193 (R107 obs-norm independence) — supports figure caveat
- All 11+ mechanism CLMs (R86-R117) — figure anchors them
- CLM-0225 (this round)
