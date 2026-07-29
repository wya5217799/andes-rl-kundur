# LINE — ICEMS 2026 → SCI 期刊扩展线 (专属上下文)

> **新会话入口**: 凡是做这篇稿子 (手稿、修订、补实验、投稿) 的会话, 先读本文件,
> 再按指针取细节。本页只放决策与状态, 论证一律不复制正文。
> 注册于 `memory/RESEARCH_PROGRAM.md` 的 `## Manuscript lines`;账本留痕见 `memory/claims/CLM-0620.md`。

## 身份与优先级

- **线**: ICEMS 2026 会议论文 (`paper/icems2026/main.tex`, 结论: 集中式 TD3 胜共享 MARL,
  MARL 无增量价值) → SCI 期刊扩展版。
- **优先级**: **发 SCI 为当前第一目标** (2026-07-29 作者/PI 显式决策)。
  注: 与 AGENTS.md 优先级链 (correctness → … → manuscript 排最后) 存在张力,
  该重排只适用于手稿线工作分配, AGENTS.md 未改。

## 锁定决策 (2026-07-29)

1. **路线 A**: 期刊扩展版, 不另起炉灶。
2. **创新点结构 (iii)**: 机理为主轴 + 泛化为验证。
3. **理论深度 (b)**: 半解析 (小信号/特征值), 不做 Lyapunov 全理论。
4. **创新点布局** (调研 §7): C1 主轴 (学习版惯量空间配置, 对接 Poolla/Dörfler 谱系);
   C2 弱电网泛化作为 C1 的验证段; C3 稳定证书视进度作一节; C4 (FRT/暂态) 不做。
5. **目标期刊**: 主 **IJEPES** (中科院 2025 版大类 2 区, IF 5.3, JCR Q1),
   备 **EPSR** (大类 3 区, IF 4.3, 审稿快); 冲选项 MPCE (2 区, IF 6.2, Gold OA 必付 APC);
   IET GTD 已降 4 区, 排除。依据: `JOURNAL_TARGET.md`。
6. **负结果如实保留**: MARL 无增量价值作为方法论贡献写, 不抢救不粉饰。

## 当前状态 (截至 2026-07-29)

- **R280** `CENTRALIZED-EXPLANATION-SUFFICIENT` (CLM-0610): 集中式 TD3 相对 q=0
  同步损失 -24.35%、前三秒区域间 IAE -17.04% (三种子一致); 共享 MARL 也有效
  (-16.79% / -9.54%) 但比集中式差 ~9-10%, 无架构增量。
- **R281** `MECHANISM-PARTIAL` (CLM-0615): 差动分配→区间模态阻尼映射成立但非全局
  单调 (学习方向满幅 +55%, 反向 +9.5%, U 型上翘); VSG 本地模态 1/√M 折中;
  总惯量减半时分配敏感度翻倍 (+53%) → 弱电网轴第一个实测锚点。
- **R282** `UPTURN-REAL` (CLM-0625): 4 点加密确认 U 型上翘是同支真结构 (5 对相邻
  余弦 1.0, |Δf|≤0.0009 Hz, ζ 平滑单调 0.01939→0.02132), 非模态串线 artifact;
  识别规则已搬进脚本 (R281 离线识别追认有效)。CLM-0615 措辞原样成立。
- **R283** `STRENGTH-GRADIENT-CONFIRMED` (CLM-0630): Q-0043 双轴扫描 (24 点)。
  电气轴 (SCR 代理 k∈{1.0,1.5,2.0}) 全有效: S 比 4.48 单调, 弱电网下 U 型消失
  转单调、学习方向增益 +55%→+159%; 惯量轴有效级 S 比 2.30, 低惯量 hybridization
  区识别 flag (开 Q-0044, 未授权)。C2 弱电网段有实测梯度。
- **R284** `LEFT-FLANK-SMOOTH` (CLM-0635): 左翼加密 4 点全连续 (余弦 1.0,
  |Δf|≤0.003 Hz), ζ 0.03023→0.02528 平滑单调 — U 型左翼同样无串线。
- **R285** `ZONE-CHARTED` (CLM-0640): 20 格 M0×q 地图画完识别盲区边界
  (M0≥175 全 q 可测; 125/150 仅 |q|≤0.125; 100 碎裂); flag 归因 = VSG 本地
  模态在低惯量大分配下压过区间支 (6/7), 非数值故障。Q-0044 closed-positive。
- **R286** `SURVIVES` (CLM-0645): Q-0045 零训练迁移评估 — 冻结 centralized
  臂在联络走廊 r/x ×k (k∈{1.5,2.0}) 下重跑封存 24 场景, 192/192 全过。k=2.0
  时同步损失 −22.333% [−27.066,−15.686]、区域间 IAE −17.345% [−24.307,−9.795],
  名义增益保留 ≥92%; 扰动位置四分位全部保住双位数改善, 增益非位置 artifact。
  弱网重训问题按判定树不开启。Q-0045 closed-positive。
- **机理段写法**: 只能是有界经验陈述 (R281 verdict 判定依据原句), 禁止"分配创造
  阻尼"与单调律; U 型为确认结构, 成因未解释不编。
- **C2 段写法**: 按 R283 实测梯度写 ("扫描范围内电网越弱分配越重要"); SCR 代理
  必须写成声明式联络走廊电抗缩放, 不换算真 SCR 单位; 惯量轴只写有效级 +
  hybridization 警告 (低惯量区 unmeasured 不是 absent)。时域存活句按 R286 写
  ("增益在走廊电抗 1.5–2 倍下保留 ≥92%, 四个扰动位置均保持"); 位置分组只作
  描述 (n=6, 不称显著)。
- **问题状态**: Q-0042 closed-partial; Q-0043 closed-positive @ R283;
  Q-0044 closed-positive @ R285; Q-0045 closed-positive @ R286 (programme
  列表已回 [])。**SCI 线实验侧到此全部完成, 剩下全是写。**

## 待决岔口 (需 PI/作者拍板)

- **(已解决 2026-07-29)**: C2 动笔前的 hybridization 区摸底 — R285 已画完边界,
  R286 已补时域存活, C2 证据链闭环, 可以动笔。
- **(无未决岔口)**: 下一动作 = C2 段正式起草 (骨架已有, feed 数字齐)。

## 手稿骨架 (调研 §7 推荐, 未动笔)

经典谱系提出空间配置问题 → 因果实验证明实时差动配置确有增益 → 小信号分析解释
增益来源与决定量 → 弱电网扫描给出边界 → (可选) 约束设计向稳定证书的工程逼近。

## 资产指针

| 内容 | 路径 |
|---|---|
| 深度调研报告 (~180 篇语料, 创新点 C1-C4) | `paper/sci_upgrade_survey/REPORT.md` (+ `corpus/`) |
| 对 Yang 2023 / Ge 2026 差异化备忘录 (引言 + cover letter 草稿) | `paper/sci_upgrade_survey/DIFFERENTIATION_MEMO.md` |
| 期刊分区查证与主备决策 | `paper/sci_upgrade_survey/JOURNAL_TARGET.md` |
| 会议版手稿 | `paper/icems2026/main.tex` |
| 机理实验数据/溯源 | `results/r281_eig_mechanism/`, `results/r282_eig_upturn/`, `results/r283_strength_sweep/`, `results/r285_hybridization_map/` |
| 时域弱网存活数据/溯源 | `results/r286_weak_grid_td/` (+ seal `memory/rounds/R286/weak_tie_seal.json`) |
| 实验 feed 报告 (论文草稿直接取料, 契约 `skills/kundur-round/SKILL.md` §3) | `paper/sci_upgrade_survey/reports/` (已有 R281–R286) |
| 段落骨架 (C1 机理段 + C2 弱电网段, PI 过目用, 非投稿文本) | `paper/sci_upgrade_survey/draft/sec_C1_mechanism_skeleton.md`, `sec_C2_weak_grid_skeleton.md` |
| 正式评估数据/溯源 | `results/r279_formal_evaluation/`, `results/r280_r279_action_audit_correction/` |

## 诚实边界

写作时不可越过的五条线, 见 `DIFFERENTIATION_MEMO.md` §4 (不创造阻尼、不宣称
MARL 无用、不贬低先行工作、不宣称泛化、不暗示覆盖慢恢复回路)。

---
*本文件随手稿线演进就地更新; 发表后从 `RESEARCH_PROGRAM.md` 注册表移除并归档。*
