# R284 verdict — 左翼加密 (R282 对称补全)

**Date**: 2026-07-29
**Status**: LEFT-FLANK-SMOOTH (valid, guards 全过)
**Type**: experiment
**Wall**: ~0.5h
**Question**: 无 (手稿线确认轮, R282 对称补全; 不开不闭 programme 问题)

## TL;DR

在 q∈[-0.25,-0.1875] 加密 4 个 EIG 点, 左翼与右翼同样平滑连续: 5 对相邻
余弦全 =1.0、|Δf|≤0.003 Hz, ζ 从 0.03023 平滑单调降到 0.02528, 有益侧无
隐藏结构. ζ-q 图左右分辨率对称, 手稿机理图无左翼 caveat.
实质见 feed `paper/sci_upgrade_survey/reports/R284.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**: R282 加密了右翼, 左翼还是 R281 的粗网格, 审稿人看图会问
"左边怎么不加密". 这轮在 q∈[-0.25,-0.1875] 对称补 4 个点, 契约全冻.

**结果 (一句话)**: 左翼干干净净——5 对相邻点模态身份全连续 (余弦 1.0),
阻尼从 3.02% 平滑降到 2.53%, 没有隐藏结构; ζ-q 图现在左右同分辨率, 该
画的图可以定稿了.

**意外**: 无 (这正是我们想要的结果——有益侧就是平滑单调, 没有第二个惊喜).

**对手稿的含义**: 机理图 M1 左右对称加密完毕; 机理段结构段只需一句
"有益侧单调性在加密分辨率下平滑" 收口, 无任何新 caveat.

**我默认下一步做**: 按计划开 R285 (Q-0044 hybridization 区绘图, 先去
programme 授权), 然后 R286 时域弱电网.

**你想插一脚就说**: 无口子——这轮是纯对称保险, 结果无歧义.

---
Feed: `paper/sci_upgrade_survey/reports/R284.md`; 数据:
`results/r284_eig_left_flank/`; claim: CLM-0635.
