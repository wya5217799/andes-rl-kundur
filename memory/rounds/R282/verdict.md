# R282 verdict — U 型上翘真伪确认 (4 点加密)

**Date**: 2026-07-29
**Status**: UPTURN-REAL (valid, guards 全过)
**Type**: experiment
**Wall**: ~0.5h
**Question**: 无 (手稿线确认轮, CLM-0615 follow-up; 不开不闭 programme 问题)

## TL;DR

在 q∈[+0.1875,+0.25] 加密 4 个 EIG 点确认 R281 的 U 型上翘是真结构不是模态
切换 artifact: 5 对相邻点参与向量余弦全 =1.0、|Δf|≤0.0009 Hz (阈值 0.05),
同一区间模态 ζ 平滑单调 0.01939→0.02132. CLM-0615 的非单调措辞原样成立.
实质见 feed `paper/sci_upgrade_survey/reports/R282.md`.

## Questions opened (this round)

- (none)

## Questions closed (this round)

- (none)

## Questions advanced (this round, status unchanged)

- (none)

## 给 PI 的话

**这轮干了啥**: 上轮你说 U 型上翘可疑, 这轮在 q∈[+0.1875,+0.25] 加密 4 个
点验真伪, 纯 EIG 重算, plant/映射/守卫/识别规则全冻, 只改网格.

**结果 (一句话)**: 上翘是真的——5 对相邻点模态身份全连续 (参与向量余弦
1.0, 频率跳变 ≤0.0009 Hz), 同一模态阻尼从 1.94% 平滑爬到 2.13%, 不是模态
串线 artifact; CLM-0615 的"非全局单调"措辞不用改.

**意外**: 识别规则这轮搬进了脚本, 重算 R281 两端点和上轮离线手认的值完全
一样——R281 的离线识别被追认有效, 以后 EIG 轮都走脚本内识别, 不再有
不可复现的离线步骤.

**对手稿的含义**: 机理段的 U 型从"疑似 artifact"升级为确认结构, ζ-q 图右
侧可以画成平滑曲线; 措辞仍是有界经验陈述, 上翘的物理成因没解释, 不编.

**我默认下一步做**: 开 R283 (Q-0043 已授权 rank 130): 惯量轴 M0×q 15 点 +
电气轴联络线电抗 k×q 9 点扫描, 顺手补 R281 的 M0=100/q=-0.25 识别断点.

**你想插一脚就说**: 如果你担心左端 (q→-0.25) 也藏着类似结构, 我可以再加密
左侧 4 点, 脚本现成只改网格.

---
Feed: `paper/sci_upgrade_survey/reports/R282.md`; 数据:
`results/r282_eig_upturn/`; claim: CLM-0625.
