# R463 verdict — 独立指标复算通过，有限日程类仍无全约束解

**Date**: 2026-08-21  
**Status**: completed  
**Type**: experiment  
**Wall**: ~0.3h（含两次已保留的后继纠错、严格序列化、独立复算和完整约束数据导出）

## TL;DR

有效分类为 `U4-GUARD-AUDIT-VALID`。24 条原始轨迹的全部物理与动作指标和既有实现逐项完全一致；350 个有限日程在四个工况上的精确枚举没有全约束可行解，最优日程的最大超限为 0.526936%，由边界感知动作总变差触发。15 份原训练清单均未保存实际约束成本或乘子轨迹；30 单元后验诊断已完整导出但不得冒充原训练。

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- Q-0112 remains open; this schedule-shared four-profile enumeration is not the observation-history information-class program.

Feed: `paper/yang_md_decoupling_marl/reports/R463.md`

## 给 PI 的话

**发生了什么**：我们把原始仿真记录中的频率、变化速度、不同方向之间的干扰和动作压力全部重新算了一遍，结果与原统计逐项一致。随后把三百五十套候选方案在四种工况下全部穷举检查，没有遗漏失败样本，也没有把无效数据当成零。

**这说明什么**：在这批明确列出的候选方案里，没有一套能同时满足所有要求。最接近的一套只在最坏要求上超出约半个百分点，主要卡在动作变化过多；这只是对这批有限方案的精确结论，不能说所有智能控制方法都做不到。旧训练还确认没有保存约束成本和乘子变化过程，所以不能事后编造训练轨迹。

**下一步做什么**：继续整理灵敏度、近似误差、鲁棒性和统计检验所需的数据，再启动已经规划的训练对比。新训练必须完整保存每轮约束成本和乘子变化，并沿用已经通过检查的实际执行动作记录规则。
