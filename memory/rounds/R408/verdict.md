# R408 verdict — V2 solving gate: Q-ENTRY at bandpass K=3.5

**Date**: 2026-08-15
**Status**: completed — Q-ENTRY
**Type**: experiment
**Wall**: ~30 min formal execution (17 arms x 30 records, 8 workers) + telemetry supplement

## TL;DR

R408 validly completes all 510 records with zero guard errors, reproduces the
R407 endpoint at K=0.1, and finds the frozen single-family 0.4 Hz ring-edge
bandpass entering Q at K=3.5 (r_d 0.938947, r_cross 0.539791) and K=4.0
(r_d 0.911541, r_cross 0.515282), all guards and the strict cross gate
passing. The P6 small-gain anomaly is resolved as a reference-semantics
artifact (K->0 limit = zero-action arm at 1.202733) with a quantified
negligible port-map leak; the two frozen blends fail bounded.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R408.md`

## 给 PI 的话

**发生了什么**：按照外部数学方案给出的方向，我们把同一个带通阻尼环节的强度从原来的小范围继续加大，并在全部五百一十条已披露仿真记录上正式检验。结果在强度取三点五和四点零时，两个核心指标同时达标（机组之间差异部分的能量降到基准的九成四和九成一，交叉串扰响应降到五成四和五成二），所有保护与有效性检查全部通过；此前"小强度时指标异常"的疑团也查清了：那不是控制器的毛病，而是对比基准的定义问题——强度归零时系统退回到"什么都不做"的那一档，本来就不等于基准。另外两个外部方案的混合结构都未通过，但主线已经不需要它们。

**这说明什么**：可行区域在这个结构类里不是空的——之前两轮实验说"没有强度能同时达标"，是因为当时的搜索范围太小、在边界处就停了，而不是理论上不可能。外部方案的数学分析（预测三点五附近应达标）与实际测量高度一致（差异部分的误差不到百分之一）。这给论文提供了一个正面的构造性结果：一种确定性的、只用本机与两个邻居信息的控制办法，就能同时压低机组差异能量与交叉串扰响应。

**下一步做什么**：当前结果是在已披露的开发数据上得到的，按预注册规则，接下来单独开一轮"未见数据"的检验门：用同一结构、强度三点五，在从未用过的评估数据组上复验。通过后，本结果才能进入论文正文；同时按既定约定更新线路导航与资产登记。

## 技术路径

- 下一动作: bandpass K=3.5 的单独 held-out 门(新证据轮, 单独领号)。
- 归档: r408_v2_solving_gate 四件套 + telemetry_supplement, 均已 sha256。
- 后续 scratch: 无(MARL 路线保持关闭; 若 held-out 门通过, 按线路 owner 决策进入论文)。
