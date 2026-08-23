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
- **简化按证据** (吸收自 dsh-find-simplifications): 强候选 = 无生产消费者 /
  仅测试·文档引用且非 load-bearing / 同一事实两份表示 / seam 方法无人用 /
  纯测试支撑包 / speculative generality / 为未用 API 守护的不变式 /
  手写重实现依赖。拒绝 = 有生产 caller (feature 决策非清理)、被决策或
  defensive pattern 背书、只换 churn、太小 → TODO。全仓审计走 ask-matt。

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
- **门生命周期 (ADR-0020)** — 硬门分 locked (科学/复现/人话层, 永不降级)
  与 soft (模型能力守卫). soft 门 clean 轮数 ≥ threshold 可降级
  hard→warn→advisory. 永久降级要 operator 批准; 长任务免批走
  `provisional` (一步, TTL 自动过期, 可 ratify) 或提前 `grant` 预授权.
  降级 = 授权随后的治理编辑放松该规则, 本身不改 CLAUDE.md; 复发 `flag`
  自动回升 hard 并清 provisional. registry:
  `docs/repo-hygiene/gate-registry.json`, 勿手改.

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

### Engineering flow and bug-finding

Scoped code work — feature, refactor, bug — not a research round, routes
through two peer engineering routers, never the round/claim/feed ledger:

- Build / spec / multi-file change → `ask-matt`: idea → spec → tickets →
  `/implement` (drives `/tdd` + `/code-review`). Default for a non-trivial
  `scratch` slice.
- Broken / flaky / regressed → `diagnosing-bugs`: tight red loop first, then
  fix + regression test.

Boundary and invocation: `docs/repo-hygiene/external-skills.md`.

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

### External theory intake

外部数学/理论解答 (GPT Pro / theory-audit / 外部 solver) 进项目先三分 —
代数恒等式 / 机制预测 / 论文级命题 — 各走不同路径 (R422/R424/R432 教训:
机制结论只吸收一半、事后补算)。**任何机制预测/假设 — 无论来自外部解答
还是内部诊断推导 (R435 教训) —** 强制: plan 写可观测清单 (进 seal 或登记
`not-pursued`) + feed 写回裁决 (`supported`/`refuted`/`undecidable`)。
evidence 收尾前跑 `python memory/tools/external_theory_intake_lint.py R<N>`
(与 `objective_semantics_lint.py` 同级)。契约全文 (三分执行、清单模板、
论文级四证、裁决格式) 见
`skills/kundur-round/references/external-theory-intake.md`。

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
- **归档/合并按未来决策价值, 永不按字数·年龄** (吸收自
  dsh-archive-agent-notes): 判这条 rationale 还会约束未来改动吗? keep = 负保证 /
  持久边界 / 复现条件 / 安全规则 / 重新引入条件; archive = 一次性 UI / 已闭合
  minor bug / 被取代实现细节 / 当前行为别处显然。字数与年龄只是发现线索,
  不是归档判据。

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
- **无泄漏写作** — feed/claim/verdict 技术骨架视角 = 仓库非会话; 禁死设计
  会话引用、变更叙述、评审编排、hedge; 精简 cap 时保命题不删事实. 判定
  `skills/kundur-round/references/prose-leakage.md`, probe
  `cot_leakage_lint.py`.
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
- **草稿批次更新契约**: 草稿本体只在批次节点更新 — manuscript lane 轮 /
  manuscript-refresh / 提交冻结; feed 收尾不改稿 (SKILL.md §2-g)。feed 的
  `Manuscript mapping` 段 = 草稿待更新清单单一真源 (feed_check 强制), 批次
  更新时逐条对照, 不另建清单副本; mapping 断言与草稿现有文字冲突时 feed
  当场标 `CONFLICT` 防漏改。草稿滞后于最新 feed = 正常状态; 证据权威在
  feed/claim, 草稿只是出口。

模板: `memory/rounds/_TEMPLATE_VERDICT.md`. 历史 verdict 正文不回填改写.

## Tools (细节看各工具 docstring; 这里只记什么时候用)

- 分流: 先分流、再领 round。纯离线 implementation / 既有 development-data
  prototype 走 `scratch`；scratch 每个 red-green slice 只跑定向测试。新
  ANDES/训练、受保护资产改动或 claim/question/title 影响才 prospectively
  升级到 `evidence`。完整规则 canonical 在 `skills/kundur-round/SKILL.md` §2。
- 方向恢复: 下一技术路线不清、历史路线过多或准备再换算法时，先按
  `skills/kundur-round/references/technical-route-census.md` 盘点五家族，
  再用 `technical_route_census.py validate` 强制检查全覆盖、唯一归类与终端
  选择；盘点默认留在 `tmp/<line-id>/`，不建立第二 evidence ledger。
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
  `close_round.py RNN completed|superseded|aborted` (关轮后默认提交工作区,
  `--no-commit` 跳过; 每轮两个提交点 = seal 后 `round R<N>: seal` +
  关轮自动提交, render 后 STATE.md 有变补 `ledger: refresh STATE.md render`,
  见 `skills/kundur-round/SKILL.md` §2 步骤 4/5).
- 跨 round/job/artifact/scratch 的非权威控制视图用
  `research_control.py`; 它不启动科研命令、不提升证据，契约见
  `docs/repo-hygiene/research-control.md`.
- reward-ablation claim 后必跑 `dual_metric_lint.py`.
- 改目标/loss/reward 加项的 round 收尾前必跑
  `objective_semantics_lint.py R<N>`（语义门，R424 教训：plan 带
  `penalty_direction_probe` 标记 + rehearsal 留梯度方向探针记录）.
- 引用外部数学/理论解答的 round 收尾前必跑
  `external_theory_intake_lint.py R<N>`（外部理论吸收门，R422/R424/R432
  教训；机制预测须有可观测清单或 not-pursued 登记）.
- 吸收外部审查包 (deep review) 的 round 收尾前必跑
  `external_review_intake_lint.py R<N>`（外部审查吸收门，R474/R475 教训：
  包须登记 ARTIFACTS + 哈希核验 + 逐 finding 处置 + feed 裁决；守卫 G.5）.
- 写含 "Holm/materiality/超过10%" 措辞的 claim 后必跑
  `materiality_statistics_lint.py <CLM-id>`（材料性统计口径门，R473 教训：
  "Holm-controlled" 必须是边界处直接检验的 Holm，零效应 p + bootstrap CI
  下限不算；守卫 G.3；R473 数据诊断 zero-null p=1/64 过而 materiality-null
  p=2/64 不过）.
- 写 feed/claim/verdict 后跑 `cot_leakage_lint.py R<N>`（无泄漏 recall
  battery，advisory 不阻塞；判定与处置见
  `skills/kundur-round/references/prose-leakage.md`）.
- 打分复用: `scripts/score_run.py` (paper-grade ranker).
- 门生命周期: `gate_lifecycle.py list|audit|provisional|ratify|grant|demote|flag` —
  治理规则降级/免批路径/回升 (ADR-0020). 想放松某条硬门先 `audit`.
- GPT Pro 数学问题打包: 用户输入「提取数学问题」(或近似, 如「数学问题数据
  压缩包」) → `python memory/tools/gpt_pro_pack.py` 打包 open+partial 问题 +
  相关数据 → 交付 zip 路径 + 内附 README/SHA256SUMS。问题清单/状态/相关
  数据只改 `memory/tools/gpt_pro_manifest.json`, 不改工具。聊天上传限 512MB
  用 `--max-size-mb 512`: 工具自动拆成两个**独立可解压** zip (禁手搓二进制
  分卷 — Windows/聊天界面都打不开, 2026-08-22 返工教训)。
- 外部答案包吸收: 用户给聊天空文件夹或说「吸收/这是结果」 →
  `python memory/tools/external_answer_absorb.py --src <folder> --line <line>`
  一次完成嵌套同名目录定位、ASCII 改名、SHA256SUMS 核对、重复检测与登记
  片段生成 (REGISTER.md; 手搓三次的 2026-08-22 教训)。登记片段由 agent 抄入
  ARTIFACTS/manifest/gate-log, 工具不自动改账本。每包结论必须对照仓库封存
  证据裁决, 不照单全收 (deep-solutions 包把 U1/U5/U8 标 INCOMPLETE 是它只读
  markdown 没读 npz, 以封存轮次为准)。

## 代码约定

- **ANDES = WSL only**: `/home/wya/andes_venv/bin/python` (Git Bash 需
  `MSYS_NO_PATHCONV=1`). Windows 侧 ANDES 是历史误装, 别用.
- **ANDES 工作目录隔离**: 维护中的训练/评估/round 入口统一经
  `scripts/andes_scratch.py` 启动, 保留 scratch 于 `tmp/andes/`; 禁止直接
  在仓库根运行并留下 `kundur_full_out.*`.
- **长命令后台跑**: 预计 >5min 的 ANDES/train/eval 命令必须后台 job, 禁止
  同步阻塞 (harness code-run 有 10min wall-clock ceiling, 撞了就白跑)。
  后台后不轮询、等 job 完成通知再续 (轮询烧 token)。启动多小时仿真前先
  确认它确为当前 round 所需 —— 误判长任务 = 最大浪费。
- **默认 env: `andes_vsg_env_v4`** (paper-faithful, ZERO_G4_INERTIA=True).
  V5 (REGCA1) 是 paper-deviation, opt-in only (ADR-0004).
- **改 env / train.py 前**必读 `docs/eng-notes/NOTES_ANDES.md`.
  `OBS_AREA_MEAN_FREQ_AUG` 默认关: 开启改 obs_dim, 与历史 ckpt 不兼容.
- **V4 regression**: `tests/test_v4_env_regression.py` 1e-9 tol 必须绿.
- **No Simulink 1:1 chase** (ADR-0005). ANDES = single platform of record.
- 并行预算: 不设固定 WSL Python 进程数。Owner 常设授权 (2026-08-17 晚):
  硬件有富余即并行 —— 同线并发 round 是默认姿态; 富余判据 = 实测并发
  负载阶梯 (rungs 1/2/4/8/12/16, 对方负载在场下重测) + 总内存记账
  (全部并发活训练 RSS + 3 GiB OS 底 ≤ WSL MemTotal), 不是固定常数。
  R339+ 的正式 plan 必须在 seal 前用当前机器的容量证据冻结
  `host_process_budget`，声明本任务完整 `wsl_python_processes`（including
  child and process-pool workers，并计入 launcher）和全部在飞轮的
  `other_reserved_processes`；两者之和不得超过整机预算。预算一经封存不得
  按结果改动；在飞轮被新轮声明后其环境不得被静默再改。正式并行时每个
  进程的 native numerical-library threads fixed to one；分区、拟合与验证等
  封存边界仍串行。正式 ANDES 执行的 rehearsal/封存顺序见 `kundur-round`
  evidence lane。已冻结的旧轮次保持其原进程数，不追溯改写。
- 布局: `src/andes_rl_kundur/` 包结构, 见 `docs/adr/0001-src-layout.md`.
- Issue/triage/agent 文档约定: `docs/agents/`.

## 活跃研究规则 (现状)

- **AI-only compactness**: new/edited AI rules/state = caveman short clauses + pointers + one fact/one home (fact allocation -> `kundur-round` §3).
- **AI-facing writing default**: agent-reader docs (`AGENTS.md`, `CLAUDE.md`,
  `skills/`, `docs/agents/`, `docs/repo-hygiene/`, ledger templates) are
  written per the global `writing-for-agents` skill — load it before creating
  or editing one. Schema-enforced ledger contracts keep their `validate.py`
  shapes; boundary: `docs/repo-hygiene/external-skills.md`.
- plan 与 verdict 技术骨架可用紧凑中文；question/claim/feed 用英文。
  给 PI 的正文必须用完整、自然、无术语的中文，不能用 caveman 省略句。
- **说人话 (交互层)**: 与 owner 提问/解释/汇报时, 完整自然中文、一次只问
  一个问题、不堆术语缩写; 技术复盘只进 plan/feed/claim, 对话只讲人话。
- **owner 要效率 = 免批授权**: owner 说「拉满硬件/别管规则/为效率改规则」
  时, 走 `gate_lifecycle.py` grant/provisional 免批路径或按 owner 明示直接
  执行, 别硬顶规则拒绝 — 规则挡 owner 意图是摩擦, 记进 session_friction 复盘。
- **Plateau (R86)**: algo dim 结构性 plateau 已证, 别起 algo SOTA-hunt rounds.
- **Research priority (fallback only)**: correctness and objective validity →
  residual mechanism → topology generalisation → safety/stability →
  cross-simulator/HIL → manuscript.
- **新架构 (R82)**: TD3-Transformer / TD3-LSTM2 ≤ R72_w4 baseline
  (CLM-0144/0145); Transformer deterministic-eval collapse 是 known issue.
- 当前论文目标只由本次 `session_context.py --line <id>` 的结果决定。
  `priority` 只供未指定论文时回退，不代表长期唯一主线。
- **实验设计护栏 (2026-08-22 三包吸收)**: 新实验 plan 写设计段前必查
  `skills/kundur-round/references/experiment-design-guardrails.md` (来源干预
  必须同拍 replica wiring 不许外生 donor; feasibility-before-training;
  证书阶梯; 概率声称口径; 执行动作语义; 下一轮优先级)。偏离要 owner 授权
  并写进 plan。
- **工作流优化触发**: 用户输入「优化工作流」(或近似表达) 时, 复盘聊天历史
  找出用着不舒服的工作流 (反复手工步骤 / 被绕过的规则 / 事后补救 /
  返工 / 靠报错兜底), 按根因启动优化 — 教训 codify 进 infra (工具 / lint /
  规则进 CLAUDE.md + memory/tools), 不记笔记。复盘用
  `python memory/tools/session_friction.py` (DSH 会话 zstd 日志 → 摩擦信号
  排名 + owner 纠正引语), 再按根因 codify。报告: 找到的痛点 + 根因 +
  优化了什么。
- **外部 agent 会话纪律 (2026-08-23)**: Codex 复盘教训 codify 为
  AGENTS.md `会话工作纪律` (task queue / freeze-then-review / once-then-grep /
  long-run background / 说人话) + `session_friction.py --artifact` (外部会话
  包直接复盘, 不再手工解压)。同类协作问题不再另立规则, 指向该节。
- **harness 层优化**: 摩擦根因在 agent 组合层 (工具集 / persona / 呈现 /
  压缩) 时, 改专属预设 `~/.dsh/.agent-presets/kundur/` 而非 memory/tools。
  该预设 standard 基底 + 原生呈现 (非 PTC; bind-fail 按会话折算 PTC 更高,
  证据与摩擦→杠杆映射表见该目录 README.md), persona 锚三条高频摩擦
  (read-before-write / 长命令后台不轮询 / 说人话)。改前 `session_friction.py
  --all` 复测, 改后 owner 开新会话验证工具清单与 persona 生效。
