---
round: R141
state: active
opened: '2026-05-19'
closed: null
supersedes_rounds: []
superseded_by_round: null
abort_reason: null
superseded_note: null
---
# R141 plan — Algo-class breakdown of bimodal cluster (refines CLM-0264)

**Status**: ACTIVE → CLOSED-POSITIVE
**Opened**: 2026-05-19
**Driver**: PI "继续". R139 default next (option b) — quick algo-class
breakdown of degenerate cluster to test "is attractor selection
algo-conditional?".
**Parent**: CLM-0264 (R139), CLM-0118, CLM-0204

## TL;DR

Classify 91 ckpts by algo (SAC / TD3-MLP / TD3-LSTM / unknown) using
label regex, tabulate per-algo cluster fractions.

Result: **non-LSTM algos cannot reach LSTM SOTA cluster** (0/8
combined). LSTM SOTA cluster is **algo-exclusive** (35/38 known LSTM,
3 unknown likely LSTM, 0 SAC/MLP). LSTM training fails to degenerate
in 37% of runs.

Degenerate cluster splits into:
- 4 "deliberate cum_rf-optimised" (MLP/SAC, paper SOTAs per CLM-0118)
- ~28 "failed-training" (LSTM, cum_rf -0.09 to -0.60)

Zero ANDES.

## Wave 顺序

| W | Content | Wall |
|---|---|---|
| W1 | python regex classify + tabulate | ~10 min |
| W2 | CLM-0268 + verdict + render | ~20 min |

## 资源冲突 gate

R83-R139 done; WSL free ✅. Read-only ✅.

## 资产保护契约

不动: any code, V4, ckpt, test, R135 / R139 outputs.

新建:
- `memory/rounds/R141/{plan.md, verdict.md}`
- `memory/claims/CLM-0268.md`

## Cross-references

- CLM-0264 (R139 bimodal) — direct refinement
- CLM-0118 (multi-controller / cum_rf SOTA) — context
- CLM-0204 (warm-h_0 env-side) — degenerate sub-cluster characterised here
- CLM-0268 (this round)
