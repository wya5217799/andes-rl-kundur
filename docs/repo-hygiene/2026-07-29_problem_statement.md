# 仓库治理问题陈述（Repo Hygiene Problem Statement）

- 日期: 2026-07-29
- 状态: 问题定义（不含修复方案，不含 skill 实现）
- 触发: PI 反馈 "仓库越来越乱，论文和代码混在一起，流程产物给人感觉杂乱"
- 方法: 全量实地勘察（根目录 / memory / results / paper / scripts / docs / git 状态），
  所有结论附路径与数量证据，不凭印象。

## 0. 总体判断

`memory/` 系统（claims/questions/rounds/notes + validate.py / render.py /
reserve_*.py）治理良好，对人和 AI 都可靠。

乱在 `memory/` 之外。乱的方式不是"没有规则"，而是**规则只覆盖流程前半段**：
实验→结果 有契约（round 目录、verdict 骨架、feed 分工，2026-07-29 起），
分析→论文 没有等价契约。属于"账本很严、下游放养"。

## 1. 问题清单（按严重度排序）

### P1 · 论文存在分叉副本，无人声明真源 —— 最严重 ✅ 2026-07-29 已裁决

> **裁决结果**：`paper/icems2026/`（与 E:\Projects checkout 逐字节一致，
> tex 16:17 / PDF 16:23）为唯一最终版；`paper_review/icems2026/` 旧版
> （tex/PDF 16:12）已归档至 `_legacy/paper_review_icems2026_superseded_20260728/`；
> `output/pdf/icems2026_full_paper.pdf` 已覆盖为最终版字节。
> 两版实质差异：final 版的 prose 更精确（置信区间与图注措辞），
> 架构图术语从 "rank-one"/t 索引 改为 "zero-sum"/k 索引。
> 比对证据留档 `tmp/paper_truth_compare/`（gitignored）。

- `paper_review/icems2026/` 是 `paper/icems2026/` 的整树拷贝且已漂移：
  `diff -rq` 显示 `main.tex`、`build_figures.py`、`figures/control_architecture.tex`、
  `figures/dynamic_response.pdf`、`figures/paired_effects.pdf`、`main.pdf` 全部 differ。
- `output/pdf/icems2026_full_paper.pdf` 是第三份 PDF 拷贝。
- 一篇论文三个物理副本、内容不一致。违反 CLAUDE.md "第三份拷贝是 fork"
  原则的精神，但该原则只管 claim 数据表，没管论文本体。

### P2 · 单仓库承载 ≥4 条交付线，无交付线边界

- `paper/icems2026`（会议论文）、`paper/sci_upgrade_survey`（SCI 手稿线）、
  `研究计划/proposal`（中文名 LaTeX 目录，违反仓库 ASCII 约定）、
  `docs/research/external_A报告/`。
- 各线内部结构不一致：icems2026 用 `working/`，sci 线用 `reports/ + draft/ + corpus/`。
- 新交付线的唯一创建方式是新开顶层目录 → 顶层目录只增不减。

### P3 · 分析代码有三个互相竞争的家

- CLAUDE.md 明文：分析逻辑写进 `probes/`（可复现）。
- 现实：`scripts/` 里有 `analyse_*` / `audit_*` / `eval_*` 一大批分析评估脚本；
  `paper/icems2026/build_figures.py` 把图代码嵌进论文目录（并随 P1 被复制漂移）。
- `probes/` 仅 19 个文件，`scripts/` 有 107 个——规则指定的家反而更空。

### P4 · `scripts/` 无生命周期管理，违反仓库自己的原则

- CLAUDE.md 原则 1："不写 one-off scripts"。
- 现实：`scripts/` 顶层 107 个脚本，`scripts/_archive/` 只收编 20 个；
  归档机制存在但无触发条件，等于没有。

### P5 · 流程产物（分析文档）无 schema，散落 ≥8 处

memory 只有 claim/question/round/note 四种实体，但流程实际还产出：

| 产物类型 | 实际住处 |
|---|---|
| 调研 / landscape / 审计 | `docs/research/`（11 个日期前缀文件） |
| 论文评审报告 | `quality_reports/ars_icems2026_review/` |
| 计划类文档 | `quality_reports/plans/` 与 `docs/superpowers/plans/` 两处 |
| feed 报告 | `paper/<line>/reports/`（有契约，正面案例） |
| 工程笔记 | `docs/eng-notes/` |
| 教学产物 | `lessons/`、`reference/`、`MISSION.md`、`NOTES.md`、`RESOURCES.md` |
| 历史遗留 | `_legacy/`、`docs/R37-R41_summary.md` |

同一种"分析产生的文档"无实体类型、无命名约定、无索引。
流程产出物的类型系统只有账本那一半。

### P6 · 根目录是杂物间

- `=0.4`：`pip install ruff>=0.4` 重定向笔误产生的日志文件。
- `kundur_full_out.npz`（7.6 MB）、`kundur_full_eig.txt`（232 KB）仿真输出落根目录；
  `.gitignore` 只挡 `kundur_full_out.*`，漏了 `eig.txt`。
- 9 个顶层 Markdown（AGENTS / CLAUDE / CONTEXT / MEMORY / MISSION / NOTES /
  README / RESOURCES）。`MEMORY.md` 描述的 memory 布局已过时（无 questions/、
  无 feed 契约）；`MISSION/NOTES/RESOURCES` 是某次教学会话产物。
  新人 / 新 AI 有 5 个互相竞争的"先读我"入口。

### P7 · 临时目录六重人格

`tmp/`（gitignored）、`.tmp/`（不在 gitignore，内有 skill 安装残留
`ars-skill-install`）、`.pytest-temp-r279-001/`、`.pytest_cache/`、
`.mypy_cache/`、`.ruff_cache/`。临时空间无统一约定。

### P8 · git 卫生失控

- 95 个未提交变更（勘察时 `git status --short | wc -l`）。
- `memory/RESEARCH_PROGRAM_CLOSED.md` untracked，但已被
  `memory/RESEARCH_PROGRAM.md` 正文引用（引用了 git 不认识的文件）。
- `LICENSE` untracked。
- `main.pdf` 二进制被追踪，每次编译产生 diff 噪音。

### P9 · 文档互相指路但内容漂移

- CLAUDE.md 说启动步骤 canonical 在 `skills/kundur-round/SKILL.md` §1，
  但 CLAUDE.md 自己又写了一遍启动步骤（指针与副本并存）。
- `MEMORY.md` 布局图停在旧 schema。
- "文档跟代码一起改"原则无执法者。

### P10 · skill 体系双轨，边界无文档

- `skills/kundur-round`（仓库内生，CLAUDE.md 指定 canonical）与
  `external_skills/academic-research-suite`（整套 vendored 外部 skill，
  自带 agents/commands/audits）并存，分工无说明。
- `.claude/`、`.codesearch.db/`、`.understand-anything/` 三层 AI 工具状态堆在根目录。

## 2. 根因（三条）

1. **治理覆盖率不对称**：实验账本有类型系统 + 工具执法；账本之后的一切
   （论文、图、分析文档、评审、教学产物）只有口头约定。产物数量一涨，
   放养的半边必然显乱。
2. **结构增长方式是"加顶层目录"而非"归入既有类型"**：没有先例约束新产物
   该住哪，每个新需求都发明一个新家。
3. **卫生规则无执法者**：原则齐全（不写 one-off、单一真源、文档同改），
   但没有任何 lint 检查根目录清洁、副本漂移、归档触发。
   `dual_metric_lint.py` 能 lint 研究结论，没有任何东西 lint 仓库本身。

## 3. 对两个未来通用 skill 的锚点（仅锚点，非 skill 规格）

- **"整理代码库" skill 要解决的问题面**：P1（副本漂移）、P4（脚本归档）、
  P6（根目录）、P7（临时目录）、P8（git 卫生）、P9（文档漂移）。
  通用性来源：这些都是"产物位置 / 副本 / 生命周期"问题，与具体研究内容无关。
- **"优化流程" skill 要解决的问题面**：P2（交付线边界）、P3（分析代码的家）、
  P5（分析文档 schema）、P10（skill 分工）。
  通用性来源：给"账本下游"补类型系统，模式可迁移到任何
  实验→分析→写作 的研究仓库。

## 4. 非目标（本轮明确不做）

- 不写任何 skill 本体。
- 不做任何文件移动 / 删除 / 归档。
- 不裁决 `paper/` 与 `paper_review/` 谁是 icems2026 真源（需 PI 决策）。

## 5. 证据快照（2026-07-29 勘察值）

- `results/`: 379 个 run 目录 + 181 个散落 log；MANIFEST whitelist 表仅 1 条。
- `memory/`: claims 295 / questions 46 / rounds 272 / notes 26 / handoffs 12 / tools 19。
- `scripts/`: 顶层 107 + `_archive/` 20。
- `probes/`: 19。
- `docs/research/`: 11 个日期前缀文档。
- git: 95 个未提交变更。
