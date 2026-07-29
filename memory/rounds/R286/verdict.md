# R286 verdict — Q-0045 弱联络走廊时域存活 + 扰动位置依赖

**Date**: 2026-07-29
**Status**: SURVIVES (valid, 192/192, 守卫全过)
**Type**: experiment
**Wall**: ~2.5h (8 分片并行, 单条 ~275-286s)
**Question**: Q-0045 → closed-positive by CLM-0645

## TL;DR

零训练迁移评估: 冻结 R279 臂 (q0 + centralized 三种子) 在同一封存 24
场景库上把 7↔8 三回联络走廊 r/x 乘 k∈{1.5,2.0} 重跑. 双主端点在两个
k 级都保持材料性改善且保留 ≥92% 名义增益 (k=2.0: 同步损失 −22.333%
[−27.066,−15.686], 区域间 IAE −17.345% [−24.307,−9.795]) — 判定树
SURVIVES, 弱网重训问题按预注册规则不开启. 扰动位置读: 四个位置全部
保住双位数改善, 增益不是位置 artifact. 实质见 feed
`paper/sci_upgrade_survey/reports/R286.md`.

## 执行备注

- 冒烟先行: 单场景 q0×k=2.0 确认注入 (Line_4/5/6 x: 0.22→0.44) 与单条
  墙钟 (233s), 再封盘全量.
- 裁剪顺序未触发: 两个 k 级 × 4 臂全量跑完, 未砍任何臂/级.
- 首版内联启动命令被 Git Bash/wsl 双层引号吞掉循环变量, 改启动器文件
  (`scripts/run_r286_weak_grid_td.sh`) 后正常 — 与 R279 的 launcher
  惯例一致, 记为流程经验.
- 计划资产清单写的是 `reports/R286.md`, 实际按 R283–R285 惯例落
  `paper/sci_upgrade_survey/reports/R286.md`.

## Questions opened (this round)

- (none) — 判定树 SURVIVES, 弱网重训候选问题按预注册规则不开启.

## Questions closed (this round)

- Q-0045 → closed-positive, by CLM-0645 (SURVIVES)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**: 把 C2 弱网段从"只有线性化证据"补上时域这一脚. 冻结的
集中式控制器不换权重, 直接在联络走廊电抗 1.5 倍和 2 倍的电网上重跑
封存的 24 个场景, 192 条仿真一条没挂.

**结果 (一句话)**: 增益活着——走廊电抗翻倍, 同步损失改善只从 −24.3%
掉到 −22.3%, 快速区域间端点几乎没动 (−17.0%→−17.3%), 判定树
SURVIVES, 不用开弱网重训.

**意外**: 名义增益按扰动位置分两档 (老负荷点 ~−37%, 新母线负荷
~−20%), 走廊变弱后两档收敛到同一档——增益不是挑位置挑出来的;
四个位置在 k=2.0 全部保住双位数改善.

**对手稿的含义**: C2 段现在有时域存活句可写 ("增益在联络走廊 1.5–2 倍
电抗下保留 ≥92%, 且不依赖扰动位置"), 跟 R283 的小信号梯度方向一致,
C2 证据链 (线性化梯度 + 盲区边界 + 时域存活) 闭环. SCI 线的实验侧
到此全部完成, 剩下全是写.

**我默认下一步做**: 关 Q-0045, programme 列表回 []; 手稿线进入 C2 段
正式起草 (骨架在 `paper/sci_upgrade_survey/draft/`, R286 数字已进
feed). 若想先把走廊 k 扫到 2.0 以上或换走廊定义, 需要新授权, 默认不做.

**你想插一脚就说**: 如果你担心审稿人挑战 "k≤2 够不够弱", 说一声——
我可以预注册一个 k∈{2.5,3.0} 的扩展扫描 (同管线, 约 1.5 小时机时),
默认不做.

---
Feed: `paper/sci_upgrade_survey/reports/R286.md`; 数据:
`results/r286_weak_grid_td/`; claim: CLM-0645.
