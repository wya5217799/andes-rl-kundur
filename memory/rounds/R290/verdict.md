# R290 verdict - topology initialization root cause bounded

**Date**: 2026-07-30
**Status**: ROOT-CAUSE-BOUNDED-NO-VALID-PATH
**Type**: diagnostic
**Question**: Q-0047 closed-partial by CLM-0665

## TL;DR

Direct `.u.v` mutation caused R289's initialization failure; the public
`Line.set` path fixes initialization. The Line_2/q0 positive pair persists
identically after valid pre/post-setup application, so no registered method is
eligible for a topology-value matrix. Q-0047 closes partial. Full evidence is
in `results/r290_topology_initialization/FEED.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0047 -> closed-partial by CLM-0665. The current topology set cannot support
  a valid information-value gate; the value question itself remains
  unmeasured.

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**：把 R289 的问题缩到一个三秒级最小复现，只看 q0 和 Line_2 开断；然后逐项比较直接改数组、官方 `Line.set`、刷新连通性和 setup 前设置四条路径，同时把动作顺序改成显式列表并加了回归测试。

**结果（一句话）**：根因拆清了，但没有可继续跑价值矩阵的合法路径。直接写 `.u.v` 确实导致初始化失败；换成 `Line.set` 后初始化和残差全部正常，但 Line_2/q0 仍稳定出现两个正实部特征值，最大实部 0.0458362。

**意外**：setup 前设置、setup 后 `Line.set`、再加 connectivity refresh 三条合法路径得到完全相同的正实部结果。这说明它不是刚才那个初始化 bug 伪造的谱，而是当前模型和运行点下这个开断本身过不了 q0 小信号守卫。

**流程修复**：以后线路状态只能走模型 setter；EIG 不能只看返回 True，还必须检查 `TDS.test_ok`、`exit_code`、残差和正实部。动作库必须用显式 order 列表，不能依赖 JSON 字典顺序。两道防线都已经有测试。

**下一步**：Q-0047 以 `closed-partial` 停止。我们没有证明拓扑信息有价值或没价值，只证明当前候选集不具备合法测量条件。若以后重开，必须新建问题，并在 seal 前预注册 q0 初始化与小信号可行性筛选；现在不自动换线、不重跑矩阵、不训练 GNN，也不进 LaTeX。

---
Feed: `results/r290_topology_initialization/FEED.md`; diagnostic:
`results/r290_topology_initialization/diagnostic.json`; claim: CLM-0665.
