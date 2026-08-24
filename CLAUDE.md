# andes-rl-kundur — AI navigation

## 工程原则 (load-bearing — 改任何代码前必读)

三条按优先级排序. 冲突时 **原则赢**.

### 1. 可维护性

- **不写 one-off scripts** — 同一 housekeeping pattern 出现第二次, 升级成
  `memory/tools/<name>.py` (library + CLI). 模板: `close_round.py`.
- **每工具 self-documenting** — top docstring 含 motivation + usage + 失败模式.
- **不依赖 cwd** — 用 `Path(__file__).resolve().parents[N]` 自找 ROOT.
- **跨平台 ASCII fallback** — Windows GBK terminal 显示不了 ✓/✗, 统一 ASCII.
- **文档跟代码一起改** — 改 CLAUDE.md / 模板是改动的一部分.
- **简化按证据** (dsh-find-simplifications): 强候选 = 无生产消费者 / 仅测试·文档引用
  且非 load-bearing / 同一事实两份表示 / seam 无人用 / 纯测试支撑包 /
  speculative generality / 为未用 API 守护的不变式 / 手写重实现依赖. 拒绝 = 有生产
  caller / 被决策或 defensive pattern 背书 / 只换 churn / 太小 → TODO. 全仓审计走 ask-matt.

### 2. 鲁棒性

- **原子领号 (race-safe)** — round/claim ID 只能 `reserve_round.py` /
  `reserve_claim.py` 领. **永远不手动挑号**.
- **失败优雅** — WSL 不可用 / YAML 错 / 文件读失败: 返回空, 不 crash.
- **multi-metric 双轨制 (CLM-0430)** — paper-reward-ablation 类 claim 必须同 cite
  `geo` (项目 11-axis) + `cum_rf` (paper Yang2023 §IV-C). 两 metric 可能反方向.
  Lint: `python memory/tools/dual_metric_lint.py`.
- **measured > estimated** — baseline 用 `baselines.py` 查 measured, 绝不 cross-algo
  比例外推 (R246 估错 baseline 烧 10 轮, CLM-0410→CLM-0435).
- **预期 vs 实际配对** — plan.md 写 pre-registered outcomes, verdict 对照分类.
- **拓扑状态与 EIG 硬门 (CLM-0665)** — 线路开断只能经
  `evaluation/topology_status.py::apply_line_outage()` / ANDES `Model.set`,
  禁止直接写 `Line.u.v`. `PFlow.run()` / `EIG.run()` 返回 True 仍不够;
  paper-facing EIG 必须同时过 `TDS.test_ok`, `exit_code=0`, 初始化残差,
  finite spectrum 和 positive-real guard. 动作遍历只读显式 order 列表.

### 3. 长期发展

- **不动 paper-cited assets without 新 round** — `paper_grade_axes.py` (Asset 4),
  `base_env.py`, `andes_vsg_env_v4.py`, `train.py`: 改前必读 `docs/eng-notes/NOTES_ANDES.md`,
  改动要新 round + claim (path-only 重命名也算).
- **不打破 ckpt 命名空间** — V5 走 `r80+_*`, V4 走原命名. R57+ 全 SOTA ckpt 依赖
  V4 bit-identical.
- **不追已证结构性的方向** — R86 已证 algo dim plateau structural (91 trials 共识,
  CLM-0148/0149). 突破在 reward shaping / env physics / classical baseline, 不在 algo 调参.
- **教训 codify 进 infra** — session 出失败 → 写 validator/linter/tool 防再犯.
  进 `memory/tools/` + CLAUDE.md 才算, `memory/handoffs/` 记笔记不算.
- **plan-first for non-trivial** — 跨 file / 跨 layer / 改 contract 先 plan 后写.
- **门生命周期 (ADR-0020)** — 硬门分 locked (科学/复现/人话层, 永不降级)
  与 soft (模型能力守卫). soft 门 clean 轮数 ≥ threshold 可降级
  hard→warn→advisory. 永久降级要 operator 批准; 长任务免批走 `provisional`
  (一步, TTL 过期, 可 ratify) 或提前 `grant` 预授权. 复发 `flag` 自动回升
  hard 并清 provisional. registry: `docs/repo-hygiene/gate-registry.json` 勿手改.

## Read first (会话启动)

冷启动跑 `python memory/tools/session_context.py --json` (点名手稿
`--line <id>`, 未知 id 先 `--list-lines`), 只读它返回的 bounded
`required_reading`; 完整步骤 canonical 在 `skills/kundur-round/SKILL.md` §1.

- `memory/STATE.md` 是自动渲染 oracle, 需要全局状态时按需读, 永不手改.
- 老上下文用 `python memory/tools/note_query.py --topic <t> [--grep <kw>]`,
  不批量加载 handoff / claims / rounds.
- 术语问题读 `CONTEXT.md`; ADR 本体在 `docs/adr/`.

## Agent skills

- **路由唯一真源**: `docs/repo-hygiene/skill-routing.md`; 一任务至多一个 primary skill,
  仓库私有 authority > 外部方法, explicit > implicit, availability != invocation.
- **项目/外部 skill**: 项目只暴露 `kundur-round`; 自维护分支是其内部 reference,
  不独立调用. 外部安装/边界见 `docs/repo-hygiene/external-skills.md`; 适配只住
  `skills/kundur-round/references/research-skill-adapter.md`; type scope 见 `docs/repo-hygiene/type-checking.md`.
- **Issue/domain**: `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md`, `docs/agents/domain.md`, `CONTEXT.md`, `docs/adr/`.
- **外部理论**: 三分吸收 + observable/feed/close gates → `skills/kundur-round/references/external-theory-intake.md`.

## 记忆系统 (R39+)

四实体: Claim / Question / Round / Note; handoff 不进 schema, STATE.md 永不手改.
形态、引用、归档: `skills/kundur-round/references/ledger-writing.md`.

## Round 文件契约 — feed 分工

每次实验的实质内容**只写一遍, 写在 feed 报告**; 账本两件套瘦成骨架.
过程 canonical = `skills/kundur-round/SKILL.md` §1-3; 本节只持 validate.py 强制的骨架.

- **plan.md**: 生命周期状态只住 YAML frontmatter `state`; 正文禁止 **Status** 行.
- **feed 报告** (`paper/<line>/reports/<slug>.md`; 无手稿线 `results/<run>/FEED.md`):
  内联数字挂 claim id, 其余指 results 文件, 不复制数据表.
- **verdict.md 骨架** (validate.py 强制): `**Status**:` + `## TL;DR` (≤3 句) +
  Questions opened/closed/advanced 三节 + feed 指针在 `## 给 PI 的话` 之前 +
  给 PI 的话 (完整自然中文, 无编号/术语; R291+ verdict ≤80 非空行).
- 分析 seam (probes/ vs src/ vs scripts/) 与生命周期 + 流水线路径纪律: `docs/repo-hygiene/executables.md`.
- 数据归档: 结论承载 JSON 必须有 `.sha256`; R291+ 本轮 results 先登记
  `results/MANIFEST.md`; 未登记第二副本只能标 `LOCAL-ONLY`.
- 无泄漏写作: `skills/kundur-round/references/prose-leakage.md`; probe `cot_leakage_lint.py`.

## 手稿线

导航契约、生命周期、哈希快照、草稿批次更新:
`skills/kundur-round/references/manuscript-lines.md`; 步骤 SKILL.md §5.
模板: `memory/rounds/_TEMPLATE_VERDICT.md`.

## Tools (什么时候用; 细节看各工具 docstring)

- 分流: 先分流、再领 round (scratch / manuscript / evidence; evidence 先领号).
  完整规则 SKILL.md §2.
- 方向恢复: 五家族盘点 `technical_route_census.py validate`, 盘点留 `tmp/<line-id>/`.
- 开工: `reserve_round.py --strict-no-active [--line <id>] --write-plan-stub` →
  写 plan → `round_preflight.py R<N>` (exit 2 = BLOCK, exit 1 = WARN).
- 收尾: `reserve_claim.py --round R<N>` → feed → publication gate
  (`skills/kundur-round/references/publication-gate.md` + `memory/tools/feed_check.py`) →
  claim 注册卡 → verdict 骨架 → `validate.py` → `render.py` → 给 PI 的话贴对话.
- 查 baseline: `baselines.py --match <ref_run>` (measured, 别估).
- 状态/查询/关轮: `status.py` / `query.py --tag / --best` / `close_round.py RNN
  completed|superseded|aborted` (关轮默认提交工作区, `--no-commit` 跳过).
- 跨 round/job/artifact 控制视图: `research_control.py`.
- 门生命周期: `gate_lifecycle.py list|audit|provisional|ratify|grant|demote|flag`.
- Lints (按 claim 类型): `dual_metric_lint.py` / `objective_semantics_lint.py R<N>` /
  `external_theory_intake_lint.py R<N>` / `external_review_intake_lint.py R<N>` /
  `materiality_statistics_lint.py <CLM-id>` / `cot_leakage_lint.py R<N>` (advisory).
- 打分复用: `scripts/score_run.py`.
- GPT Pro 数学打包: 用户「提取数学问题」→ `gpt_pro_pack.py` (清单只改
  `gpt_pro_manifest.json`; 512MB 用 `--max-size-mb 512` 自动拆两个独立 zip).
- 外部答案包吸收: 用户「吸收/这是结果」→ `external_answer_absorb.py --src <folder> --line <line>`.

## 代码约定

- **ANDES = WSL only**: `/home/wya/andes_venv/bin/python` (Git Bash 需
  `MSYS_NO_PATHCONV=1`). Windows 侧 ANDES 是历史误装, 别用.
- **ANDES 工作目录隔离**: 统一经 `scripts/andes_scratch.py` 启动, scratch 住
  `tmp/andes/`; 禁止仓库根直跑留 `kundur_full_out.*`.
- **长命令后台跑**: 预计 >5min 的 ANDES/train/eval 必须后台 job, 禁止同步阻塞
  (10min wall-clock ceiling, 撞了白跑). 后台后不轮询、等完成通知. 启动多小时
  仿真前先确认它确为当前 round 所需 — 误判长任务 = 最大浪费.
- **默认 env: `andes_vsg_env_v4`** (paper-faithful, ZERO_G4_INERTIA=True).
  V5 (REGCA1) 是 paper-deviation, opt-in only (ADR-0004).
- **改 env / train.py 前**必读 `docs/eng-notes/NOTES_ANDES.md`.
  `OBS_AREA_MEAN_FREQ_AUG` 默认关: 开启改 obs_dim, 与历史 ckpt 不兼容.
- **V4 regression**: `tests/test_v4_env_regression.py` 1e-9 tol 必须绿.
- **No Simulink 1:1 chase** (ADR-0005). ANDES = single platform of record.
- **并行预算**: 不设固定 WSL Python 进程数; 富余判据 = 实测并发负载阶梯
  (rungs 1/2/4/8/12/16) + 总内存记账 (活训练 RSS + 3 GiB OS 底 ≤ WSL MemTotal).
  R339+ 正式 plan 必须在 seal 前冻结 `host_process_budget` + `wsl_python_processes`
  + `other_reserved_processes`, 封存后不得按结果改动; formal 并行 native
  numerical-library threads fixed to one. 顺序见 SKILL.md evidence lane.
- 布局: `src/andes_rl_kundur/` 包结构, 见 `docs/adr/0001-src-layout.md`.

## 活跃研究规则 (现状)

- **规则预算**: CLAUDE.md ≤160 行; 新规默认下放 pointer, `repo_health` 强制.
- **AI-only compactness**: new/edited AI rules/state = caveman short clauses + pointers + one fact/one home.
- **AI-facing writing**: agent-reader docs 改前 load `writing-for-agents`; schema shape 不变.
- 技术资产 caveman; question/claim/feed English; owner 对话/PI 正文完整自然中文, 一次一问.
- **owner 要效率 = 免批授权**: 按明示或 `gate_lifecycle.py` grant/provisional 执行.
- **Plateau (R86)**: algo dim 结构性 plateau 已证, 别起 algo SOTA-hunt rounds.
- **Research priority fallback**: correctness/objective → mechanism → topology → safety → HIL → manuscript.
- **新架构 (R82)**: TD3-Transformer/TD3-LSTM2 ≤ R72_w4; Transformer eval collapse known.
- 当前论文目标只由 `session_context.py --line <id>` 决定; `priority` 只供回退.
- **实验设计**: 新 plan 前读 `skills/kundur-round/references/experiment-design-guardrails.md`.
- **工作流优化**: `session_friction.py` → 根因进 infra; harness 改前 `--all`, 改后新会话验.
- **外部 agent 摩擦**: `session_friction.py --artifact` → AGENTS.md `会话工作纪律`.
