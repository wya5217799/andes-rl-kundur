# 项目专注 ANDES, 放弃 Simulink 1:1 对标

**Date:** 2026-05-19
**Status:** accepted

## Context

paper Yang2023 (Sec.IV-A) 仿真平台 = MATLAB-Simulink，Python 通过接口控制。
本项目实现平台 = ANDES (Python TDS, 仅 WSL)，路径见 `docs/eng-notes/NOTES_ANDES.md`。

历史上 (R01..R36) 项目隐含追求 "Simulink → ANDES 1:1 复现 paper 数字"，但：

- ANDES `kundur_full.xlsx` 用 GENROU + GENCLS，paper Simulink 风机 / load model / line damping / TDS solver 细节 paper 文字未给。
- R08 verdict §2 Finding 2: H=300 物理极限下 max_df 仍 2× paper，归因 "系统其他参数差异 (line / load model / SBASE) / TDS solver / disturbance 注入方式" — 全部无法从 paper 文字反推。
- R10–R17 forensic 120 min wall 投入 0 root cause，确认 "找 Simulink 默认值匹配 ANDES" 路径回报为零。
- CONTEXT.md `V4 env` 条目已默认 ANDES 单平台。`paper path` 定义全部基于 ANDES 流程。

事实上项目 ANDES-only 已既成事实，但 grill (R80 准备阶段) 揭示这个决策在文档上隐含，未来 round 仍可能反复纠结 "要不要找 Simulink 原始 case 对账"。

## Decision

项目正式停止追求 Simulink 1:1 复现。**研究和写作 framing 基于 ANDES 实现自洽**：
- ANDES 数字 = 项目 canonical（V4 paper path，V5 工程升级）
- paper Yang2023 = 算法 / 拓扑 / reward 设计参考，**不是数字对账基准**
- 残留 2× max_df 等量级差异：归为 "platform difference"，不再当成 bug 投入修

## Considered Options

- **维持 1:1 对标追求** — 拒绝：R10–R17 + R08 已证明 ROI 为零。
- **重建 Simulink 复制路径并行验证** — 拒绝：项目 1 人 / 单 WSL session 资源约束，无法维护双平台。
- **ANDES-only 显式化** — 选中。

## Consequences

- 未来 round 不再开 "Simulink calibration" 路径。R09 副线 (line/load/SBASE audit) 仍可做，但目标是 "ANDES 自洽参数 sanity"，不是 "对齐 Simulink"。
- paper writeup 在 platform 章节明示 ANDES, 不模糊化为 "power system simulator"。
- 与 paper 数字差异 (max_df / 6-axis) 在 writeup 中作为 platform-attributable diff 说明，不当 contribution gap 自责。
- handoff / 未来对话出现 "回 Simulink 对账" 提议时，回指此 ADR 拦掉。
