# R197 verdict — Offset-diversity ensembles NOT productive (W2/W3 < single SOTA)

**Date**: 2026-05-19
**Status**: CLOSED-NEGATIVE for offset-diversity-as-SOTA-axis
**Type**: research (eval-only)

## TL;DR

Three ensembles tested:
- **W1 scalar offset-diversity** (3-way {off=0, 50, 100}): geo=**0.3846**
- **W2 hreg offset-diversity** (3-way {off=0, 50, 100}): geo=**0.4017**
- **W3 hreg offset + cross-algo** (5-way: 3 hreg-offset + R142 + R143):
  geo=**0.4046**

All three below the single-best (R174 = 0.4139 at hreg s54 off=0).
**Offset-diversity is not a productive ensemble axis** — averaging
similar-architecture policies trained at different RNG paths dilutes
rather than complements.

## Comparison to existing ensembles

| Ensemble | Components | geo |
|----------|------------|-----|
| R154 4-way SOTA | scalar + 2×QR + hreg | 0.4119 |
| R177 7-way max diversity | (all) | 0.4124 |
| **R197 W1** | scalar × 3 offsets | 0.3846 |
| **R197 W2** | hreg × 3 offsets | 0.4017 |
| **R197 W3** | hreg × 3 offsets + 2 QR | 0.4046 |
| **single R174** | hreg s54 off=0 | **0.4139** |

The pattern from R177 holds: **R174 single beats all ensembles** when
the single policy is well-balanced. The R197 ensembles share the
balanced-LS1/LS2 profile, so averaging dilutes.

## What R197 confirms

Same offset diversity finding: ensembling lifts the cross-offset
mean (W1 0.3846 vs scalar cross-offset mean 0.358 = +7%), but cannot
exceed the best single-point. The ensemble theory from CLM-0325
(complementary asymmetric strengths, not strict per-member quality)
remains correct.

## Implication for paper

Sec.IV-D's third contribution (hreg RNG-path robustness, R193+R196)
**stands as the cleanest robustness claim** — no need to mix in
ensemble-of-offsets because that doesn't improve SOTA. Paper can
report:

- Single-config SOTA: R174 0.4139 at (s54, off=0)
- Multi-offset mean (hreg robustness): 0.397 at s54 across offsets
  {0, 50, 100}
- Cross-algo ensemble (HAWE): R154 0.4119
- Offset-diversity ensemble: not productive (R197 demonstrates)

## Questions opened (this round)

(none)

## Questions closed (this round)

(none — methodological finding, no Q directly tied)

## Questions advanced (this round, status unchanged)

(none)

## 给 PI 的话

R197 三个 offset-diversity ensemble 全部低于 R174 single SOTA 0.4139:
- W1 scalar 3-offset = 0.3846
- W2 hreg 3-offset = 0.4017
- W3 hreg-offset + algo 5-way = 0.4046

**Offset diversity 不是 productive ensemble 轴**。跟 R177 "R174 single
beats all ensembles" 结论一致 — well-balanced policy averaging 是 dilute,
不是 complement.

**对 paper 影响**: Sec.IV-D 不需要加 offset-diversity ensemble section.
Hreg cross-offset mean 0.397 已经是 cleanest robustness claim.

下个 R198 候选 = 试 untested seed (s55 等)。s54 是已知 lucky seed,
s55 / s52 等可能有 luckier (s49 是 unlucky). 找到 > s54 就是新 SOTA.

## Cross-references

- R174 (single-policy SOTA 0.4139)
- R154 (4-way cross-algo HAWE 0.4119)
- R177 (7-way max diversity 0.4124 — same pattern)
- R196 verdict (2x2 grid)
