# R415 verdict — A4 额外未见 bank：三块过两块，轻惯量块差分超限

**Date**: 2026-08-17
**Status**: in-progress
**Type**: experiment
**Wall**: ~1h (含 R414 abort 后的重跑)

## TL;DR

R415 (soft-spot A4 successor) ran the frozen three-block unseen bank: the
K=3.5 bandpass passes the new-conditions and stiff-plant blocks and fails
the differential ceiling on the relaxed-inertia/heavy-damping block
(r_d 0.9712 > 0.95, all guards passing), scoping the constructive claim.

## Questions opened (this round)
- (none)

## Questions closed (this round)
- (none)

## Questions advanced (this round, status unchanged)
- (none)

Feed: `paper/yang_md_decoupling_marl/reports/R415.md`

## 给 PI 的话

**发生了什么**：我用三块从没见过的条件组合检验那台控制器：一块新的扰
动位置与强度、一块机组惯量调低阻尼调高、一块惯量调高阻尼调低。中间第
一次执行因一个记录格式细节在起步阶段就终止，我按纪律作废重跑，三块全
部拿到完整数据。

**这说明什么**：新扰动块和"惯量调高"块全部达标，且幅度富余；但"惯量
调低、阻尼调高"那块差分指标超了及格线约百分之二，虽然所有安全与执行
检查都通过。这说明这台控制器在它的固定参数下不是对所有机组状态通吃，
论文里的成功范围要明确排除这一类机组偏移——这是更诚实的边界，不是失
败。

**下一步做什么**：做计划最后一项——把确定性规则池从九种扩到二十一种
（加密增益网格加一种积分型规则），看"没有额外提升空间"的结论在更大规
则池里是否还成立；随后把四块新证据写进论文并做终稿前的全面校验。
