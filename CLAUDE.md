# andes-rl-kundur — AI navigation

## 工程原则 (load-bearing — 改任何代码前必读)

三条按优先级排序. 冲突时 **原则赢**.

### 1. 可维护性 (maintainability)

想 "6 个月后的我或别人能不能接手":

- **不写 one-off scripts** — 同一 housekeeping pattern 出现第二次, 升级成
  `memory/tools/<name>.py` (library + CLI). 模板: `close_round.py`.
- **每工具 self-documenting** — top docstring 含 motivation + usage + 失败模式.
- **不依赖 cwd** — 用 `Path(__file__).resolve().parents[N]` 自找 ROOT.
- **跨平台 ASCII fallback** — Windows GBK terminal 显示不了 ✓/✗, 统一 ASCII.
- **文档跟代码一起改** — 改 CLAUDE.md / 模板是改动的一部分, 不是 follow-up.

### 2. 鲁棒性 (robustness)

- **原子操作 (race-safe)** — round/claim ID 只能 `reserve_round.py` /
  `reserve_claim.py` 领. **永远不手动挑号**.
- **失败优雅** — WSL 不可用 / YAML 错 / 文件读失败: 返回空, 不 crash.
- **multi-metric 双轨制 (CLM-0430)** — paper-reward-ablation 类 claim 必须同
  cite `geo` (项目 11-axis) + `cum_rf` (paper Yang2023 §IV-C). 两 metric 可能
  反方向. Lint: `python memory/tools/dual_metric_lint.py`.
- **measured > estimated** — baseline 用 `baselines.py` 查 measured, 绝不
  cross-algo 比例外推 (R246 估错 baseline 烧 10 轮, CLM-0410→CLM-0435).
- **预期 vs 实际配对** — plan.md 写 pre-registered outcomes, verdict 对照分类.

### 3. 长期发展 (long-term sustainability)

- **不动 paper-cited assets without 新 round** — `paper_grade_axes.py` (Asset 4),
  `base_env.py`, `andes_vsg_env_v4.py`, `train.py`: 改前必读
  `docs/eng-notes/NOTES_ANDES.md`, 改动要新 round + claim (path-only 重命名也算).
- **不打破 ckpt 命名空间** — V5 走 `r80+_*`, V4 走原命名. R57+ 全 SOTA ckpt
  依赖 V4 bit-identical.
- **不追已证结构性的方向** — R86 已证 algo dim plateau structural (91 trials
  共识, CLM-0148/0149). 突破在 reward shaping / env physics / classical
  baseline, 不在 algo 调参.
- **教训 codify 进 infra** — session 出失败 → 写 validator/linter/tool 防再犯.
  `memory/handoffs/` 里记笔记不算 codify, 进 `memory/tools/` + CLAUDE.md 才算.
- **plan-first for non-trivial** — 跨 file / 跨 layer / 改 contract 先 plan 后写.

## Read first (会话启动)

启动步骤 (读什么、research_goal、active round 先 resume) 的 canonical
在 `skills/kundur-round/SKILL.md` §1; 这里只留仓库定向:

1. `memory/RESEARCH_PROGRAM.md` — 政策: north star / phase gates /
   priority_questions (**只列开放问题**; closed 块存档于
   `memory/RESEARCH_PROGRAM_CLOSED.md`) / `## Manuscript lines` 手稿线注册表.
2. `memory/STATE.md` — 自动渲染 oracle. 别手改, `render.py` 重生成.
3. 老上下文: `python memory/tools/note_query.py --topic <t> [--grep <kw>]`.
4. `CONTEXT.md` — glossary + 架构决策索引; ADR 本体在 `docs/adr/`.

## Agent skills

### Issue tracker

Engineering specs and tickets live in GitHub Issues. See
`docs/agents/issue-tracker.md`.

### Triage labels

Agent-facing issue states use the repository's five canonical labels. See
`docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository: domain language lives in `CONTEXT.md`
and architecture decisions live in `docs/adr/`. See `docs/agents/domain.md`.

### External skills

External skills are explicit-only adapters and have no authority over project
rounds, claims, gates, or ledgers. See
`docs/repo-hygiene/external-skills.md`.

Repository-governance type-check scope and the time-bounded legacy exception
are recorded in `docs/repo-hygiene/type-checking.md`.

## 记忆系统 (R39+)

四种 schema 实体 + handoff 草稿. STATE.md 只读 claims/questions/rounds;
handoff 不进 oracle.

| Kind | Where | Purpose |
|------|-------|---------|
| Claim (`CLM-NNNN`) | `memory/claims/` | 原子可引用 finding/decision/correction |
| Question (`Q-NNNN`) | `memory/questions/` | 开放问题, 下一轮可 address |
| Round (`RNN/`) | `memory/rounds/` | plan + verdict 绑一次调查 |
| Note (`NOTE-NNNN`) | `memory/notes/` | 外部文档索引, 非 measurement-of-record |
| Handoff (out of schema) | `memory/handoffs/` | 会话末 scratchpad |

### 写 claim 的时机与形态

- 时机: 新数字结果 (`finding`, trust V/S/T); 纠正旧数字 (`correction`,
  trust V + supersedes); 研究方向转向 (`decision`, trust S).
- 形态: **注册卡** — 一段自包含 statement (分类判定 + 主头条数字对 +
  范围短语) + provenance 指向 feed/results. 每级表格 / 位置子表 / 守卫
  明细只住 results 与 feed, 不复制进 claim — 第三份拷贝是 fork
  (单一真源分配表见 `skills/kundur-round/SKILL.md` §3).

### 开 question 的时机

verdict 记下但本轮没回答的 follow-up. statuses: open / in-flight /
closed-*. closed 必须有 closed_round (存在目录) + closed_by (存在 claim).

### 写 note 的时机

遇到外部存档文件 (handoff/ADR/eng-note/legacy doc) 值得索引:
`python memory/tools/new_note.py --source ... --topic ...` 然后填 stub.

## Round 文件契约 — feed 分工 (2026-07-29 起)

> 过程 canonical = `skills/kundur-round/SKILL.md` (会话启动 → round 生命
> 周期 → 收尾顺序 → feed 契约 → 护栏). 本节只持 validate.py 强制的
> ledger 形态; 过程细节以该文件为准.

每次实验的实质内容**只写一遍, 写在 feed 报告**; 账本两件套瘦成骨架.

- **feed 报告** (`paper/<line>/reports/<slug>.md`; 无手稿线时
  `results/<run>/FEED.md`): 唯一认真写的东西. 契约 =
  `skills/kundur-round/SKILL.md` §3 (单一真源分配表 + 节契约 + 完成
  判据). 内联数字必须挂 claim id, 其余指向 results 文件, 不复制数据表.
- **verdict.md 骨架** (validate.py 强制项, 其余正文默认不写, 内容进 feed):
  - `**Status**:` 行 + `## TL;DR` (≤3 句; 第一句被 render.py 抽进 STATE)
  - `## Questions opened (this round)`
  - `## Questions closed (this round)`
  - `## Questions advanced (this round, status unchanged)`
  - `## 给 PI 的话` (R≥59, ADR-0003; ≤30 行软上限; 五小段见模板) + 一行指向 feed
- **给 PI 的话必须原文贴进对话** (ADR-0003 chat-delivery). 指向文件不算交付.
- **分析 seam** — 影响结论的识别 / 筛选 / 有效性判定进入 `probes/`;
  可复用 implementation 进入 `src/andes_rl_kundur/`; `scripts/` 只持稳定
  execution adapter. 禁止离线手算进 verdict/feed. 事后补的判定器走
  execution amendment (R281/R283 先例). 生命周期与完成判据见
  `docs/repo-hygiene/executables.md`.

模板: `memory/rounds/_TEMPLATE_VERDICT.md`. 历史 verdict 正文不回填改写.

## Tools (细节看各工具 docstring; 这里只记什么时候用)

- 开工: `research_goal.py --json` → `reserve_round.py --strict-no-active`
  (防 context 压缩后重复开工; `--list-active` 查看) → 写 plan →
  `round_preflight.py R<N>` (exit 2 = BLOCK 修完再跑, exit 1 = WARN).
- 收尾: `reserve_claim.py --round R<N>` (先领 id, feed 内联数字要挂) →
  feed → claim 注册卡 → verdict 骨架 → (programme 问题关闭: 块归档
  `memory/RESEARCH_PROGRAM_CLOSED.md`, 列表回 []) → `validate.py` →
  `render.py` → PI 话贴对话. 严格顺序与完成判据见
  `skills/kundur-round/SKILL.md` §2.
- 查 baseline: `baselines.py --match <ref_run>` (measured, 别估).
- 看状态: `status.py`; 查 claim: `query.py --tag / --best`; 关轮:
  `close_round.py RNN completed|superseded|aborted`.
- reward-ablation claim 后必跑 `dual_metric_lint.py`.
- 打分复用: `scripts/score_run.py` (paper-grade ranker).

## 代码约定

- **ANDES = WSL only**: `/home/wya/andes_venv/bin/python` (Git Bash 需
  `MSYS_NO_PATHCONV=1`). Windows 侧 ANDES 是历史误装, 别用.
- **默认 env: `andes_vsg_env_v4`** (paper-faithful, ZERO_G4_INERTIA=True).
  V5 (REGCA1) 是 paper-deviation, opt-in only (ADR-0004).
- **改 env / train.py 前**必读 `docs/eng-notes/NOTES_ANDES.md`.
  `OBS_AREA_MEAN_FREQ_AUG` 默认关: 开启改 obs_dim, 与历史 ckpt 不兼容.
- **V4 regression**: `tests/test_v4_env_regression.py` 1e-9 tol 必须绿.
- **No Simulink 1:1 chase** (ADR-0005). ANDES = single platform of record.
- 并行上限: 单机最多 3 个 WSL python.
- 布局: `src/andes_rl_kundur/` 包结构, 见 `docs/adr/0001-src-layout.md`.
- Issue/triage/agent 文档约定: `docs/agents/`.

## 活跃研究规则 (现状)

- verdict/plan 用 caveman Chinese; question/claim/feed 用英文.
- **Plateau (R86)**: algo dim 结构性 plateau 已证, 别起 algo SOTA-hunt rounds.
- **新架构 (R82)**: TD3-Transformer / TD3-LSTM2 ≤ R72_w4 baseline
  (CLM-0144/0145); Transformer deterministic-eval collapse 是 known issue.
- SCI 手稿线 (当前第一目标): 决策与状态看
  `paper/sci_upgrade_survey/LINE.md`, 注册于 RESEARCH_PROGRAM.md
  `## Manuscript lines`.
