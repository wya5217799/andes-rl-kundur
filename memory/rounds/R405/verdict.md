# R405 verdict — candidate-A homogenization fails the disclosed gate

**Date**: 2026-08-16
**Status**: completed — GUARD-FAIL
**Type**: experiment
**Wall**: ~50 min formal execution (two registered pre-repair amendments preserved)

## TL;DR

R405 validly completes all 144 candidate-A records and reproduces the sealed
km2_kd2 reference, but the static M/D homogenization arm violates the common
no-harm ceiling and degrades both registered endpoints, so the gate classifies
GUARD-FAIL. The external solution's first-order moment prediction does not
transfer to the registered finite-window cross-energy metric on this plant.
Candidate A stops without retry; the owner-approved next step is the A+B gate.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R405.md`

## 给 PI 的话

**发生了什么**：我们按外部方案把四台机器的惯量和阻尼一次性调到彼此相同的数值，并在一百四十四条已披露仿真场景上正式检验。结果全部记录有效、参考基准也精确复现，但这种"调成一样"的做法本身把公共频率保护指标打破了（最差一项比允许值高出六成），两个核心指标也比基准差两到三倍。

**这说明什么**：外部方案的理论预测在真实物理对象上不成立——它预言的交叉改善没有出现，反而恶化。原因在于，实际验收看的是整个六秒窗口内的完整动态响应，而不是理论里的瞬时一阶量；调成一样后部分机器的阻尼反而变小，网络自身的不对称也仍然存在。真正压住交叉响应的，是基准那种随时间连续调节的动态做法，而不是一次性静态设定。

**下一步做什么**：按既定计划放弃这一单独做法，进入下一轮实验：在调成一样的基础上，叠加一个专门针对零点四赫兹振荡的带通阻尼环节，用同一套数据、同一套及格线重新检验。同时把本轮导出的全部线性化矩阵归档，供后续数学分析使用。

## 技术路径

- 下一动作: A+B 组合已披露开发门(新证据轮, 单独领号)。
- 归档: 8 剖面线性化矩阵已入 results/research_loop/r405_homogenization_gate/linearization_matrices.json。
- 后续 scratch: 由归档矩阵矩匹配恢复约减网络矩阵, 喂外部求解器做 8 维静态搜索。
