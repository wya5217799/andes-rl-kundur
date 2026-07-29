# R285 verdict — Q-0044 低惯量 hybridization 区绘图

**Date**: 2026-07-29
**Status**: ZONE-CHARTED (valid, guards+3 归因重算 1e-6 锚全过)
**Type**: experiment
**Wall**: ~1h
**Question**: Q-0044 → closed-positive by CLM-0640

## TL;DR

在冻结 plant 上铺完 20 格 M0×q 地图: 识别盲区边界成形——M0≥175 全 q 可测,
M0∈{125,150} 仅 |q|≤0.125 可测, M0=100 碎裂; 归因显示 flag 处规则抓到的是
被压惯量的 area-1 VSG 本地模态 (6/7) 或无对比度 GENROU 模态 (1/7), 即低
惯量大 |q| 下 VSG 本地模态在对比度上压过区间支. C2 段现在能精确写出梯度
"哪里测得到, 哪里测不到". 实质见 feed `paper/sci_upgrade_survey/reports/R285.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- Q-0044 → closed-positive, by CLM-0640 (ZONE-CHARTED)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**: R283 在惯量轴低端踩了 3 个识别 flag, 说不清盲区有多大.
这轮把 M0∈{100..175} × q∈{±0.125,±0.25} 铺成 20 格地图, 每格过同一个
分支有效性筛, 再对 flag 格做归因 (规则到底抓到了什么).

**结果 (一句话)**: 盲区边界画出来了——M0≥175 全范围干净, 125/150 只有
小 |q| 可测, 100 碎裂; flag 处抓到的几乎都是被压惯量那侧 VSG 的本地模态,
不是数值故障, 是本地模态在低惯量大分配下"抢镜"压过了区间支.

**意外**: 边界不是一条干净前线: M0=100 在 q=+0.25 反而重新锁定真区间支
(R283 验证过的格), 而它两边的 ±0.125 都是 flag——混杂区里规则会"跳回来",
这提醒我们边界措辞必须逐格写, 不能写成连续阈值.

**对手稿的含义**: C2 的盲区句从 "M0∈[100,200)" 升级成精确版 ("梯度在
M0≥175 全分配范围可测, 125–150 仅 |q|≤0.125 可测"); 补救路线有了名字
(分支延续识别规则), 写进 future work 一句即可, 不承诺.

**我默认下一步做**: 关 Q-0044, programme 列表回 []; 开最后一个大件
R286 (时域弱电网存活 + 扰动位置, 零训练迁移评估设计).

**你想插一脚就说**: 如果你想让我现在就上分支延续识别规则把低惯量梯度
"救回来", 说一声——那需要先立修正案再开轮, 默认不做.

---
Feed: `paper/sci_upgrade_survey/reports/R285.md`; 数据:
`results/r285_hybridization_map/`; claim: CLM-0640.
