# R484 verdict — 30-second complete guard: frozen learned policies fail; direct M/D passes

**Date**: 2026-08-28
**Status**: completed
**Type**: experiment

## TL;DR

R484 completed as a valid, hash-sealed 30-second evaluation. None of the 208
frozen R483 policies passed the complete relative physical/action contract:
126/208 met both aggregate 5% decoupling-endpoint targets, but all 832/832
policy-profile blocks exceeded both registered relative action-stress limits.
The frozen direct-M/D comparator separately passed the registered fresh-bank
Phase-1A gate on 4/4 profiles. No registered 30-second source-factor effect
established improvement above the 10% boundary after Holm control.

## Questions opened

- None.

## Questions closed

- None.

## Questions advanced

- Q-0112 remains open and is not answered by this time-domain evaluation.

## Formal decision

- Top-level result: `R484-VALID`.
- Learned-policy result:
  `R483-FROZEN-POLICIES-ALL-FAIL-COMPLETE-GUARD` on the sealed canary bank.
- Endpoint/action split: 126/208 policies meet both aggregate endpoint targets,
  while 832/832 policy-profile blocks fail both relative action-stress guards.
- Deterministic tail result: `DIRECT-MD-30S-FRESH-PASS`, 4/4 fresh profiles;
  the separate canary 4/4 result remains descriptive.
- Source-factor result: `TAIL-MATERIAL-EFFECT-NOT-ESTABLISHED`; the descriptive
  actor-by-critic estimate is not confirmatory after Holm adjustment.
- Scope: frozen policies, one topology, registered banks and 30-second
  parameter-modulation model only; no family-wide, probability, topology,
  safety, stability, hardware, deployment, zero-effect, or equivalence claim.
- Canonical feed: `paper/yang_md_decoupling_marl/reports/R484.md`.
- Claim card: `memory/claims/CLM-1520.md`.

Feed: `paper/yang_md_decoupling_marl/reports/R484.md`

## 给 PI 的话

**发生了什么**：三十秒补充评价已经完整通过数据和完整性检查。所有学习控制方案都没有通过事先约定的完整要求：不少方案确实改善了两项响应指标，但每个测试工况的控制动作强度和变化量都超过了事先允许的相对范围。作为参照的方法则在全部新测试工况中通过。

**这说明什么**：原来“学习控制整体更优”的论文叙事不能成立。现有证据支持一个更窄但清楚的结论：这些固定学习方案存在响应改善与控制动作代价之间的冲突，而参照方法在同一套三十秒要求下更稳妥。这个结果只针对当前系统和测试工况，不能推广成所有学习方法都失败。

**下一步做什么**：停止补实验和调参，立即把论文改成受证据约束的会议稿。结果部分保留动作代价冲突和参照方法通过的事实，摘要和结论删除学习方法普遍优越的表述；随后只做论文重写、图表更新和投稿检查。
