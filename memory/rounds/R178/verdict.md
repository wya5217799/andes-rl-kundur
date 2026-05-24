# R178 verdict — duplicate hreg lambda=0.001 result

**Status**: SUPERSEDED
**Date**: 2026-05-19

## TL;DR

R178 reran the same `lambda=0.001, seed=54` point as R173 and produced
bit-identical scored metrics: `geo=0.4064`, `cum_rf=-0.0686`. The plan
frontmatter already marks it superseded by R173. This verdict records
the duplicate result and closes the lifecycle gap.

## Result

- LS1: 0.3644384481915247
- LS2: 0.45309669071035874
- geo: 0.40635680730510515
- cum_rf: -0.06857841558159367

## Questions opened (this round)

- None.

## Questions closed (this round)

- None.

## Questions advanced (this round, status unchanged)

- None; this was a duplicate measurement, not new evidence.

## 给 PI 的话

R178 是 R173 的重复点，数值 bit-identical。它只证明本地复现实验一致，
不改变结论，也不需要新 claim。
