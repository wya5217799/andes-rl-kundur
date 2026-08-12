# R364 verdict — fixed-title route reset

**Date**: 2026-08-12
**Status**: completed
**Type**: analysis
**Wall**: ~2h

## TL;DR

R364 freezes the three legacy manuscript routes, establishes
`paralleled-vsg-marl` as the only active fixed-title line, and permits only
prospectively revalidated implementation reuse; no scientific evidence moves
and no simulation or training is authorized.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/paralleled_vsg_marl/reports/R364.md`

## Technical disposition

- `CLM-0970` records the programme pivot as a trust-S decision.
- `docs/adr/0015-reset-fixed-title-to-object-matched-line.md` records the
  lifecycle, object, scope, and evidence-non-transfer decision.
- The next authorized research design is the active route's per-VSG
  object/action intervention gate. A future execution requires its own
  prospective question, round, plan, and preflight.
- Controller efficacy, MARL value, stability, safety, robustness, topology
  generalization, novelty, and publication readiness remain untested.

## 给 PI 的话

**发生了什么**：先前两条路线虽然留下了训练、建模和控制资产，但不能让题目要求的关键内容在同一个实验对象中同时成立。这次保留全部旧资产和结论边界，停止把它们当作默认路线，并建立了一条只服务于当前题目的新路线。

**这说明什么**：过去的工作并非没有价值，但不同对象上的结果不能拼成同一篇论文的证据。现在研究对象、控制权限、比较方式和停止条件已经对齐；这只是方向重置，还没有证明新方法有效。

**下一步做什么**：先检查每台设备是否真的能够被独立控制、观测是否来自正确时刻、扰动是否会产生可测的设备间振荡，以及动作是否有足够余地。任何一项不成立就不开始训练，先修复实验对象；全部成立后才建立强确定性对照。
