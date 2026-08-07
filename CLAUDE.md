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
- **拓扑状态与 EIG 硬门 (CLM-0665)** — 线路开断只能经
  `evaluation/topology_status.py::apply_line_outage()` / ANDES `Model.set`,
  禁止直接写 `Line.u.v`. `PFlow.run()` / `EIG.run()` 返回 True 仍不够;
  paper-facing EIG 必须同时通过 `TDS.test_ok`, `exit_code=0`, 初始化残差,
  finite spectrum 和 positive-real guard. 动作遍历只读显式 order 列表,
  不依赖 canonical JSON 后的 mapping key 顺序.

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

冷启动跑 `python memory/tools/session_context.py --json`, 只读它返回的
`required_reading` (≤8 文件且受 contract 总字节预算约束)。完整步骤 canonical 在
`skills/kundur-round/SKILL.md` §1。

- `research_goal.py` 仍是 programme 问题选择器; `session_context.py` 在其上
  加 active manuscript 入口, 不建立新状态。
- `memory/STATE.md` 是自动渲染 oracle, 只在需要全局状态时按需读, 永不手改。
- 老上下文用 `python memory/tools/note_query.py --topic <t> [--grep <kw>]`,
  不批量加载 handoff / claims / rounds。
- 改代码或治理必读本文件; 术语问题读 `CONTEXT.md`; ADR 本体在 `docs/adr/`.

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

External skills are adapters with no independent authority over project
rounds, claims, gates, or ledgers. High-cost judgment workflows are
explicit-only; narrow presentation helpers and hard audit gates may be
implicitly selected exactly as declared in
`docs/repo-hygiene/research-skills.scope.json`. See
`docs/repo-hygiene/external-skills.md`.
Project-specific research and review rules live only in
`skills/kundur-round/references/research-skill-adapter.md`; global skill
packages must not copy them.

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
  范围短语) + provenance 指向 feed/results. R281+ verified
  finding/correction 另带结构化 `evidence_refs`: repo-relative JSON
  `path`、RFC 6901 `locator`、whole-file `sha256`、`role`. 每级表格 / 位置子表 / 守卫
  明细只住 results 与 feed, 不复制进 claim — 第三份拷贝是 fork
  (单一真源分配表见 `skills/kundur-round/SKILL.md` §3).
- R291+ statement 硬上限 1800 UTF-8 bytes；超出说明注册卡正在复制 feed，
  应缩回分类、一个头条结果与范围。

### 开 question 的时机

verdict 记下但本轮没回答的 follow-up. statuses: open / in-flight /
closed-*. closed 必须有 closed_round (存在目录) + closed_by (存在 claim).

### 写 note 的时机

遇到外部存档文件 (handoff/ADR/eng-note/legacy doc) 值得索引:
`python memory/tools/new_note.py --source ... --topic ...` 然后填 stub.
Note 只持摘要、claim candidates 与相关指针，不持 active task；未决工作必须
升级为 `Q-NNNN` 或写入当前手稿 `LINE.md`。仓库内部 `docs/adr/` 已是
canonical，不再要求另建 Note 索引。

## Round 文件契约 — feed 分工 (2026-07-29 起)

> 过程 canonical = `skills/kundur-round/SKILL.md` (会话启动 → round 生命
> 周期 → 收尾顺序 → feed 契约 → 护栏). 本节只持 validate.py 强制的
> ledger 形态; 过程细节以该文件为准.

每次实验的实质内容**只写一遍, 写在 feed 报告**; 账本两件套瘦成骨架.

- **plan.md**: 生命周期状态只住 YAML frontmatter `state`；R291+ 正文禁止
  再写 `**Status**`，避免 close 后出现 ACTIVE/COMPLETED 双真源。
- **feed 报告** (`paper/<line>/reports/<slug>.md`; 无手稿线时
  `results/<run>/FEED.md`): 唯一认真写的东西. 契约 =
  `skills/kundur-round/SKILL.md` §3 (单一真源分配表 + publication gate +
  节契约 + 完成判据). 内联数字必须挂 claim id, 其余指向 results 文件,
  不复制数据表. R281–R286 头部的 `experiment-report` 是历史名称,
  当前 canonical 就是 `kundur-round` §3.
- **verdict.md 骨架** (validate.py 强制项, 其余正文默认不写, 内容进 feed):
  - `**Status**:` 行 + `## TL;DR` (≤3 句; 第一句被 render.py 抽进 STATE)
  - `## Questions opened (this round)`
  - `## Questions closed (this round)`
  - `## Questions advanced (this round, status unchanged)`
  - feed 指针放在 `## 给 PI 的话` 之前，防止技术路径进入对话交付。
  - `## 给 PI 的话` (R≥59, ADR-0003；R≥317 按 ADR-0011): 只回答
    “发生了什么、这说明什么、下一步做什么”。先写完整自然中文；正文不出现
    英文、缩写、仓库编号、文件名、代码名或明显专业词。数字只有在直接说明
    好多少、坏多少或有没有及格时保留。
  - R291+ verdict 总计 ≤80 个非空行（硬门）；禁止复制 feed 的分析和数字。
- **两层交付** (ADR-0011): feed/claim/results/verdict 骨架保留专业名称、指标、
  编号和精确数据，供论文审计；`给 PI 的话` 是独立人话层。它必须原文贴进
  对话，指向文件不算交付；除非用户明确要求，不在它前后追加技术复盘。
- **分析 seam** — 影响结论的识别 / 筛选 / 有效性判定进入 `probes/`;
  可复用 implementation 进入 `src/andes_rl_kundur/`; `scripts/` 只持稳定
  execution adapter. 禁止离线手算进 verdict/feed. 事后补的判定器走
  execution amendment (R281/R283 先例). 生命周期与完成判据见
  `docs/repo-hygiene/executables.md`.
- **publication gate** — feed 完成有界结论后、写 LaTeX/精修图前, 直接对
  feed 做证据审计 + 电力系统领域审计; 新颖性或差异化轴未覆盖才跑 bounded
  Deep Research. 固定字段与停门见
  `skills/kundur-round/references/publication-gate.md`; 最后跑
  `python memory/tools/feed_check.py <feed>`.
- **文档预算** — 每轮 prose 默认只有 plan/feed/claim/verdict. 审核明细留
  对话或 `tmp/`; 只有成为既有 schema / ADR / issue / 注册手稿资产才持久化.
- **数据归档清点** — 结论承载 JSON 必须有 `.sha256`；R291+ 的本轮 results
  必须先登记进 `results/MANIFEST.md` 才能通过 feed/close gate。未登记私有
  第二副本时只能标 `LOCAL-ONLY`，不能称为已耐久归档。results 内不另建解释性
  Markdown；解释只住 feed。

## 手稿线作用域与文档生命周期

- 每篇文章一个 `paper/<line>/LINE.md`，声明状态、优先级、读写作用域、当前
   目标与 venue gate；它只做导航，不复制 Deep Research、feed 结论或实验
   数字。`decision_refs` 指向持久决策，`evidence_refs` 绑定 claim 与 feed；
   authoritative feed 禁止进入 `required_reading`，按 claim 懒加载。
   `verification` 段是 schema 强制项，但只许放通用执行规则或"事实在 feed"
   指针，禁止逐轮复述结论/数字——逐轮事实只住 feed，LINE 每轮只增一条
   `evidence_refs`。若 LINE 接近导航预算，优先压缩 `verification`/`stop_when`
   的复述，而不是裁剪 `evidence_refs` 指针。
  `active` 是生命周期状态，不是全局唯一主线；多条在写论文可以同时 active。
  用户明确提到某篇论文时必须用 `session_context.py --line <id>` 显式选择；
  不知道 id 时先用 `--list-lines`。只有请求未指定论文时才按 `priority`
  回退，切线不得冻结别的论文、改优先级或搬运证据。
- 每篇文章一个 `paper/<line>/ARTIFACTS.json`，登记需要持久化的调研、决策、
  草稿、图、审稿汇总与交付资产。未登记的过程输出默认住 `tmp/`。
- 一条手稿线默认只能写自己的 `write_roots`。来源会议稿、共享 results 与
  memory 只读；要修改另一篇稿子必须单独选择并授权那条线。
- Deep Research：只服务一篇稿子就登记到该线；跨线可复用才进
  `docs/research/`；探索性输出留 `tmp/`。
- 审稿：细分 reviewer 报告默认临时，只在产生长期行动或需要审计追踪时登记
  一份 consolidated review。每种 purpose 只允许一个 active canonical。
- 时间敏感文档必须有 `review_after`；输入变化或到期后标 `stale`/`superseded`，
  禁止继续作为当前决策依据。冷启动会切换到 `manuscript-refresh`，直到
  `repo_health.py check --no-baseline` 清除过期或输入漂移错误。
- 有 authoritative `experiment-feeds` 的手稿线，active `line-state` 必须在
  `ARTIFACTS.json` 对 feed 目录做哈希快照。新 feed/旧 feed 变化必须先触发
  `manuscript-refresh`；只有把最新 feed 绑定进 `evidence_refs`、核对 LINE
  当前动作与受影响 artifact 输入后才能刷新哈希，禁止只更新 hash 值。
  LINE 与冷启动集合不得超过 `docs/repo-hygiene/contract.json` 的导航预算。

模板: `memory/rounds/_TEMPLATE_VERDICT.md`. 历史 verdict 正文不回填改写.

## Tools (细节看各工具 docstring; 这里只记什么时候用)

- 分流: 先分流、再领 round。纯离线 implementation / 既有 development-data
  prototype 走 `scratch`；scratch 每个 red-green slice 只跑定向测试。新
  ANDES/训练、受保护资产改动或 claim/question/title 影响才 prospectively
  升级到 `evidence`。完整规则 canonical 在 `skills/kundur-round/SKILL.md` §2。
- 冷启动: 已知论文用 `session_context.py --json --line <id>`；未知 id 先用
  `session_context.py --json --list-lines`；未指定论文才用
  `session_context.py --json` 回退 (内部组合 research_goal + selected
  manuscript LINE; ≤8 个 required files).
- 开工: manuscript evidence 用
  `session_context.py --json --line <line-id>` →
  `reserve_round.py --strict-no-active --line <line-id> --write-plan-stub`。
  不同手稿线可各有一个 active round；缺失或 `null` 的 `manuscript_line`
  仍是全仓库锁。未指定手稿线的 programme 工作继续用
  `research_goal.py --json` →
  `reserve_round.py --strict-no-active --write-plan-stub`
  (防 context 压缩后重复开工; `--list-active` 查看) → 写 plan →
  `round_preflight.py R<N>` (exit 2 = BLOCK 修完再跑, exit 1 = WARN).
- 收尾: `reserve_claim.py --round R<N>` (只先领 id, feed 内联数字要挂) →
  写 canonical feed → 审同一份 feed 并填 publication gate → 按允许措辞完成
  claim 注册卡并回指 feed → `feed_check.py` → verdict 骨架 →
  (programme 问题关闭: 块归档
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
- **ANDES 工作目录隔离**: 维护中的训练/评估/round 入口统一经
  `scripts/andes_scratch.py` 启动, 保留 scratch 于 `tmp/andes/`; 禁止直接
  在仓库根运行并留下 `kundur_full_out.*`.
- **默认 env: `andes_vsg_env_v4`** (paper-faithful, ZERO_G4_INERTIA=True).
  V5 (REGCA1) 是 paper-deviation, opt-in only (ADR-0004).
- **改 env / train.py 前**必读 `docs/eng-notes/NOTES_ANDES.md`.
  `OBS_AREA_MEAN_FREQ_AUG` 默认关: 开启改 obs_dim, 与历史 ckpt 不兼容.
- **V4 regression**: `tests/test_v4_env_regression.py` 1e-9 tol 必须绿.
- **No Simulink 1:1 chase** (ADR-0005). ANDES = single platform of record.
- 并行预算: 不设固定 WSL Python 进程数。R339+ 的正式 plan 必须在 seal 前用
  当前机器的容量证据冻结 `host_process_budget`，声明本任务完整
  `wsl_python_processes`（including child and process-pool workers，并计入 launcher）和其他正在执行
  手稿线的 `other_reserved_processes`；两者之和不得超过整机预算。预算一经
  封存不得按结果改动。正式并行时每个进程的 native numerical-library
  threads fixed to one；分区、拟合与验证等封存边界仍串行。正式 ANDES 执行的
  rehearsal/封存顺序见 `kundur-round` evidence lane。已冻结的旧轮次保持其原
  进程数，不追溯改写。
- 布局: `src/andes_rl_kundur/` 包结构, 见 `docs/adr/0001-src-layout.md`.
- Issue/triage/agent 文档约定: `docs/agents/`.

## 活跃研究规则 (现状)

- **AI-only compactness**: new/edited AI rules/state = caveman short clauses + pointers + one fact/one home (fact allocation -> `kundur-round` §3).
- plan 与 verdict 技术骨架可用紧凑中文；question/claim/feed 用英文。
  给 PI 的正文必须用完整、自然、无术语的中文，不能用 caveman 省略句。
- **Plateau (R86)**: algo dim 结构性 plateau 已证, 别起 algo SOTA-hunt rounds.
- **新架构 (R82)**: TD3-Transformer / TD3-LSTM2 ≤ R72_w4 baseline
  (CLM-0144/0145); Transformer deterministic-eval collapse 是 known issue.
- 当前论文目标只由本次 `session_context.py --line <id>` 的结果决定。
  `priority` 只供未指定论文时回退，不代表长期唯一主线。
