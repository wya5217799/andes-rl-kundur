# R481 verdict — corrected-card fresh-holdout direct-M/D deterministic bank: DIRECT-MD-FORMAL-PASS

**Date**: 2026-08-25
**Status**: completed
**Type**: experiment
**Wall**: ~1.5h (implementation, tests, contract freeze, rehearsal, capacity, seal, 360-record formal bank, verify)

## TL;DR

R481 ran the frozen nine-law + zero deterministic bank (360 records, 16 workers, 148.06 s) on six prospectively fresh holdout profiles under the corrected card and classified DIRECT-MD-FORMAL-PASS: the development-selected winner (local_neighbour_md_km2_kd2) is guard-valid on all four evaluation profiles with decoupling ratios 0.36-0.61 versus the <=0.95 report bar.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- Q-0112 remains open; neither solved nor closed here.

Feed: `paper/yang_md_decoupling_marl/reports/R481.md`

## 给 PI 的话

**发生了什么**：这次把"不学习、按固定规则调节发电机两个关键设置的做法"和零动作参照，放在六组全新的、此前从没被任何实验看过的题目上，用修正后的仿真模型重新比了一遍。九个候选里由开发题目选出的最优者，在全部四道考核题目上都达标：两个关键指标只有门槛的一半左右，而且没有伤害频率、峰值和动作大小。

**这说明什么**：论文最重要的那句话重新站住了——不学习的做法够得着目标，而靠训练学出来的那一类方法此前够不着；而且这次的新证据是在全新题目上成立的，不依赖旧数据。但严格说这只能证明前者可行，后者是不是真的不行，还得在修正后的模型上重跑训练才能下结论。

**下一步做什么**：这轮正式收账。下一道门由你决定是否重跑学习训练和来源因素实验，在那之前训练保持关闭。
