---
line_id: sci-upgrade-survey
status: frozen
stage: frozen-derived-evidence-line
artifact_manifest: paper/sci_upgrade_survey/ARTIFACTS.json
scope:
  write_roots:
    - paper/sci_upgrade_survey
  shared_read_roots:
    - paper/icems2026
    - memory
    - results
    - docs/research
venue:
  status: shortlisted
  primary: International Journal of Electrical Power & Energy Systems
  backup: Electric Power Systems Research
  stretch: Journal of Modern Power Systems and Clean Energy
  decision_record: paper/sci_upgrade_survey/JOURNAL_TARGET.md
  official_source_status: partial
  last_checked: 2026-07-30
  review_triggers:
    - before venue-specific framing or formatting
    - before submission
    - after a material scope, ranking, fee, or policy change
objective: >-
  Preserve the ICEMS-derived literature, differentiation, venue, draft, and
  evidence-frontier assets as a read-only line; do not use it as a competing
  default route for the fixed title.
decision_refs:
  - "docs/adr/0015-reset-fixed-title-to-object-matched-line.md#decision"
  - "paper/sci_upgrade_survey/REPORT.md#section-7"
  - "paper/sci_upgrade_survey/DIFFERENTIATION_MEMO.md#section-4"
  - "paper/sci_upgrade_survey/JOURNAL_TARGET.md#decision"
  - "docs/research/2026-07-30_topology_information_value_gate.md#decision"
evidence_refs:
  - "CLM-0615 -> paper/sci_upgrade_survey/reports/R281.md"
  - "CLM-0625 -> paper/sci_upgrade_survey/reports/R282.md"
  - "CLM-0630 -> paper/sci_upgrade_survey/reports/R283.md"
  - "CLM-0635 -> paper/sci_upgrade_survey/reports/R284.md"
  - "CLM-0640 -> paper/sci_upgrade_survey/reports/R285.md"
  - "CLM-0645 -> paper/sci_upgrade_survey/reports/R286.md"
  - "CLM-0650 -> paper/sci_upgrade_survey/reports/R287.md"
required_reading:
  - paper/sci_upgrade_survey/LINE.md
  - paper/sci_upgrade_survey/draft/sec_C2_weak_grid_skeleton.md
verification:
  - Q-0047 is closed-partial and R288-R290 remain outside manuscript evidence_refs.
  - Existing C1/C2 evidence remains bound through current CLM-to-feed pointers.
  - Any adoption of new evidence updates evidence_refs and affected artifact input hashes semantically, not hash-only.
stop_when:
  - This line remains read-only and non-selectable; reopening requires a new explicit decision.
  - Its evidence frontier remains bounded through R287 and does not transfer to the successor line.
---

# SCI 升级线冻结导航

本页只保存当前动作、权限边界和可验证指针。实验数字、结论与限制分别由
claim card、feed 和 results 持有；Deep Research 与期刊判断保留在已登记原文，
不得复制进本页。

## 冻结状态

- 本线只读且不再参与默认导航；全部资产原位保留。
- 当前手稿证据前沿仍封存至 `CLM-0650 -> reports/R287.md`。
- Q-0047 已由 `CLM-0665` 以 `closed-partial` 关闭；R288-R290 只作为 programme
  诊断并保持 `stay-out`，不进入本手稿证据。正式论文正文仍未授权。

## 按需读取

- 研究路线与创新结构：`REPORT.md` §7。
- 诚实边界：`DIFFERENTIATION_MEMO.md` §4。
- 期刊短名单与锁刊条件：`JOURNAL_TARGET.md` “决策”及 Pass 2。
- 下一轮实验的取舍与停止门：`docs/research/2026-07-30_topology_information_value_gate.md`
  “Decision”。
- 数值或结果句：先开对应 claim card，再按 frontmatter 的 `evidence_refs`
  打开 feed 与其 result locator；不得从本页取数。

`ARTIFACTS.json` 是持久文档与 freshness 的注册表，由冷启动自动加入。
新 feed 会使导航失效；只有更新 evidence frontier、核对受影响派生物并通过
仓库健康检查后，才可接受新的 feed-directory hash。
