# Venue Gate 决策记录 — SHORTLISTED（2026-07-30）

**目标**：为 ICEMS 2026 的 SCI 扩展版选择“主投、备投、冲刺”路线。
**当前状态**：短名单已形成，但尚未锁刊。主投 IJEPES，备投 EPSR，冲刺 MPCE。
**没有锁定的原因**：官方 scope、作者指南与费用状态已刷新；“至少三区、保二稳三”依赖
中科院分区及本单位认定口径，现有仓库材料主要来自第三方聚合站，不能视为当前官方证明。

## Pass 0 — 投稿约束

- 首要目标：尽快完成并发表这篇 SCI，作者期望至少中科院三区，理想为二区。
- 论文类型：电力系统控制与稳定性；学习控制是手段，核心故事是 VSG 惯量空间配置机理及弱网验证。
- 扩展边界：保留“所测参数共享标量策略有效但弱于集中式 TD3”的结果，不外推到
  MARL 架构整体；不虚构 Lyapunov 证明、真实 SCR 数值或跨拓扑泛化。
- 费用偏好：不是硬性排除 OA，但锁刊前必须确认费用和报销渠道。

## Pass 1 — 当前短名单

| 顺位 | 期刊 | 官方页面当前可验证的匹配点 | 仍需作者确认 |
|---|---|---|---|
| 主投 | International Journal of Electrical Power & Energy Systems (IJEPES) | scope 覆盖电力系统建模、运行、控制和数据驱动方法；作者指南要求说明研究数据可用性，原创论文建议不超过 20 页双倍行距 | 当前中科院分区、本单位认可口径、最终页面与模板约束 |
| 备投 | Electric Power Systems Research (EPSR) | scope 宽，覆盖发输配用电系统的规划、运行、控制与保护；官方页面显示混合 OA | 当前中科院分区、本单位认可口径、转投时的篇幅与格式 |
| 冲刺 | Journal of Modern Power Systems and Clean Energy (MPCE) | scope 与现代电力系统建模、分析、控制和可再生能源接入匹配；期刊官网说明当前由赞助方承担开放获取费用 | 当前中科院分区、本单位认可口径、稿件竞争力与当期政策 |

## 决策

1. **保持 IJEPES 为主投**：论文的系统控制、VSG 机理和数据驱动控制定位与官方 scope
   最直接匹配；会议扩展到期刊所需的机理深度和弱网验证也能形成完整故事。
2. **EPSR 为低成本备投**：主题匹配宽，若 IJEPES 因故事强度或版面要求拒稿，正文结构改动相对可控。
3. **MPCE 只作冲刺项**：官方 scope 和当前 diamond OA 状态都合适，但是否值得升为主投应由论文完成后的
   新颖性、机理完整性和作者对风险的偏好决定，不能仅凭影响因子判断。
4. **不在这里确认“二区/三区”**：正式锁刊前，作者必须在本单位认可的中科院分区平台核验三刊当年口径。

## Pass 2 — 锁刊条件

只有同时满足以下条件，`LINE.md` 的 venue 状态才可由 `shortlisted` 改为 `locked`：

- C1/C2 的完整论证和图表结构稳定，摘要与贡献点可被准确概括；
- 用目标期刊近期论文做一次有边界的新颖性复核，不把普通关键词相似当作同一贡献；
- 作者确认当年中科院分区、本单位认定、OA/APC 与预算；
- 官方 Guide for Authors、伦理/数据/会议扩展要求已由 `audit-journal-submission` 刷新；
- 主投与备投的转投成本可接受。

## Pass 3 — 投稿前复核

- 在写 venue-specific framing 或套模板之前复核一次；
- 在提交前复核一次官方作者指南、费用、数据声明、会议扩展和投稿材料；
- 若论文贡献、期刊 scope、排名口径、费用或政策发生实质变化，立即把状态改为 `revalidate`；
- 任何第三方审稿周期、影响因子或分区数字只作线索，不作最终决策证据。

## 官方来源快照（2026-07-30）

- IJEPES journal page 与 Guide for Authors：
  <https://www.sciencedirect.com/journal/international-journal-of-electrical-power-and-energy-systems>
  和
  <https://www.sciencedirect.com/journal/international-journal-of-electrical-power-and-energy-systems/publish/guide-for-authors>
- EPSR journal page 与 Insights：
  <https://www.sciencedirect.com/journal/electric-power-systems-research>
  和
  <https://www.sciencedirect.com/journal/electric-power-systems-research/about/insights>
- MPCE 官方介绍与 IEEE 页面：
  <https://www.mpce.info/mpce/site/menu/20130706094849001>
  和
  <https://ieeexplore.ieee.org/xpl/RecentIssue.jsp?punumber=8685265>

下一次复核截止日期登记在 `ARTIFACTS.json`；到期或触发条件出现时，本记录仍可读取，但不得继续作为
“当前有效的锁刊依据”。
