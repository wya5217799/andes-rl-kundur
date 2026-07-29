# R283 verdict — Q-0043 电网强度扫描 (惯量轴 + 联络线电抗轴)

**Date**: 2026-07-29
**Status**: STRENGTH-GRADIENT-CONFIRMED (valid, guards+双锚点全过)
**Type**: experiment
**Wall**: ~1h
**Question**: Q-0043 → closed-positive by CLM-0630

## TL;DR

在冻结 plant 上扫两条预注册强度轴 (24 个 EIG 点): 电气轴 (SCR 代理, 联络
走廊 r,x ×k) 全有效, 敏感度 S = 0.458→1.050→2.053 (比 4.48, 单调), 弱电网
下分配权威大增且 U 型消失转单调 (+159%@k=2.0); 惯量轴 3 个有效级
S = 0.458→0.304→0.199 (比 2.30), M0=100/q=−0.25 与 M0=150/q=±0.25 为分支
串线识别 flag (脚本内可复现判定). 判定树 → **STRENGTH-GRADIENT-CONFIRMED**.
实质见 feed `paper/sci_upgrade_survey/reports/R283.md`.

## Questions opened (this round)

- Q-0044: 低聚合惯量下区间/VSG 本地模态 hybridization 区的结构
  (M0∈[100,200), q=±0.25; 由 A 轴识别 flag 区提出, 未授权)

## Questions closed (this round)

- Q-0043 → closed-positive, by CLM-0630 (STRENGTH-GRADIENT-CONFIRMED)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**: Q-0043 正式开扫: 冻结 plant 上 24 个 EIG 点, 两条先冻的
"电网强度" 轴——惯量轴 (总 VSG 惯量 ×0.5..×1.5) 和电气轴 (7↔8 联络走廊
r,x ×1.0..×2.0, 声明式 SCR 代理), 每级算分配敏感度 S, 看梯度存不存在.

**结果 (一句话)**: 存在, 而且强——电气轴全有效, 联络线越弱分配越重要
(S 比 4.48, 单调); 惯量轴有效级上同向 (S 比 2.30); 弱电网下 U 型上翘消失,
映射转单调, 学习方向的增益从 +55% 涨到 +159%. C2 弱电网段有了实测梯度.

**意外**: ① M0=150 是个 hybridization 坑: q=±0.25 处识别规则抓到根本
不是区间模态的分支 (对比度≈0, 假 ζ=0.653), 好在这轮有脚本内分支判定器
直接 flag 掉, 没让假数据进结论——R281 那个"识别断点" 也被同一个判定器
复现解释了. ② 弱电网不只放大敏感度, 还改变结构: 上翘没了, 映射变单调,
这比单纯的数字大小对手稿更有用.

**对手稿的含义**: C2 段可以按实测梯度写 (有界措辞: 扫描范围内 "电网越弱,
分配越重要"; SCR 代理必须写成声明式电抗缩放, 不换算真 SCR). 惯量轴只能
写有效级 + hybridization 警告, 低惯量区是 unmeasured 不是 absent.

**我默认下一步做**: 关 Q-0043 (closed-positive), programme 块归档, 列表回
[]; 开 Q-0044 记 hybridization 区 (不授权). 之后手稿线进入 C2 段起草准备.

**你想插一脚就说**: 如果你想先把 hybridization 区 (Q-0044) 用密集 M0×q
图摸清再动笔 C2, 说一声我就先开那个; 默认不动.

---
Feed: `paper/sci_upgrade_survey/reports/R283.md`; 数据:
`results/r283_strength_sweep/`; claim: CLM-0630; amendment:
`memory/rounds/R283/execution_amendment_20260729.md`.
