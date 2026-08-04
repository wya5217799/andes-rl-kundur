# R289 verdict - invalid sealed multigraph EIG screen

**Date**: 2026-07-30
**Status**: INVALID (five integrity failures)
**Type**: experiment
**Question**: Q-0047 remains open; advanced by CLM-0660

## TL;DR

R289 sealed the intended three circuit outages and completed all 28 EIG cells,
but the formal verdict is INVALID: JSON serialization changed the registered
action order, and four Line_2-outage cells failed the positive-real stability
guard. No topology-value estimand is interpreted. Full evidence is in
`results/r289_topology_information/FEED.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0047 -> requires a separate topology-application and initialization
  diagnostic before another value matrix can be considered.

## 给 PI 的话

**这轮干了啥**：按新规则固定了三条并联走廊单回开断，潮流预检全部通过并写入 seal；之后完整跑了名义图加三种开断、每种七个惯量分配，共 28 个 EIG 点。

**结果（一句话）**：这轮是 `INVALID`，不能拿来判断拓扑信息有没有价值。一个原因是 JSON 排序把预注册的 q0-first 动作顺序变成了字母序；另一个更重要的原因是 Line_2 开断下，q0 和三个正向分配各出现两个正实部特征值，最大实部约 0.0390 到 0.0638。

**意外**：三种开断的潮流都收敛、28 个点也都识别到了目标频带模态，名义三锚点还与 R281 完全一致；但 ANDES 在开断拓扑的 EIG 初始化中同时报告了非零残差。现在不能把正实部直接解释成真实失稳，也不能把识别出的阻尼当成控制收益。

**下一步**：不覆盖、不重跑 R289。先单独做一个很小的诊断轮，解决两件事：seal 必须显式保存动作列表而不是依赖字典顺序；线路状态必须在正确的系统 setup/初始化阶段生效，并把初始化成功本身变成硬守卫。只有这个诊断通过，才允许重新预注册信息价值矩阵。

**你想插一脚就说**：如果你希望到这里停止，我会把 Q-0047 标记为被执行有效性阻塞；如果继续，下一轮仍不训练、不做 GNN、不做时域，也不进 LaTeX。

---
Feed: `results/r289_topology_information/FEED.md`; analysis:
`results/r289_topology_information/analysis.json`; claim: CLM-0660.
