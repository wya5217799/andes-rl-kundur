---
name: kundur-round
description: andes-rl-kundur 仓库流程 canonical — 一轮研究从选题到 PI
  交付的完整步骤、feed 契约、护栏。仓库内会话经 CLAUDE.md 指针到达;
  不进全局技能目录。
---

# Kundur Round — 仓库流程 canonical

本文件是 andes-rl-kundur 研究流程的唯一过程真源。仓库事实（schema、
工具目录、代码约定、模板）留在 CLAUDE.md 与各模板文件，本文件只持
**过程**并用指针取细节。仓库根: `C:\Users\27443\Desktop\andes-rl-kundur`。

词汇: **round** = 一次可证伪调查 (plan + verdict); **feed** = 实验实质
的唯一完整写处; **ledger** = claims / questions / rounds 骨架三件套。

## 1. 会话启动 (步骤)

1. 跑 `python memory/tools/session_context.py --json`。
2. 只读输出的 `required_reading`; 历史事实按需用 `note_query.py` / `query.py`
   查, 不把整个 ledger 塞进上下文。
3. `mode=resume-round` → 先闭环 active round; `mode=research` → 用输出的
   原文 objective / verification / stop_when; `mode=manuscript` → 按当前
   LINE.md 入口完成手稿动作; `mode=idle` → 不自行开实验。
4. 改代码或仓库治理前必须读 `CLAUDE.md`, 即使当前 manuscript 入口没有把
   它列入最小阅读集。
5. 使用全局研究、写作或审稿 skill 时，先读
   `skills/kundur-round/references/research-skill-adapter.md`；项目规则不从
   全局 skill 包反向复制。

完成判据: 能说出唯一 mode、objective、authority、active scope、
stop_when；读取集合同时满足 8 文件上限和 contract 字节预算，且没有预加载
authoritative feed。

## 2. 工作量分流

领 round 前先看**下一动作**，不是看整个长期目标。只允许三条 lane：

- **`scratch`**：只读诊断、普通代码/TDD、离线数学或使用已声明 development
  数据的原型；不产生新 ANDES/训练/物理数据，不改变标题、摘要、claim、
  question 或正式 verdict，不写 sealed/paper-cited 资产。scratch 不领 round/claim，
  不写 feed/LINE/ARTIFACTS；探索输出进 `tmp/`，可复用实现和
  定向测试才进 `src/`、`probes/`、`scripts/`、`tests/`。
- **`manuscript`**：只用现有 evidence 做当前手稿线内的写作、审稿、图或
  venue 动作。只写所选 `LINE.md` 的 `write_roots`，不领研究 round；若动作
  发现新 evidence 缺口，先停并另行升级。
- **`evidence`**：新 ANDES、训练或其他物理执行；新的 holdout/comparator
  freeze；标题、摘要、claim 或 question 的支持/处置；修改 sealed evidence、
  paper-cited 资产或正式判定逻辑。任一触发即先 prospectively 领 round、写
  plan 和 preflight，再执行完整生命周期。

分流规则：

1. scratch 每个 red-green slice 只跑定向测试；pre-seal 才跑相关回归和
   preflight；round close 才跑 feed gate、repo health、ledger/render 与完整
   test suite 一次。
2. 一个 evidence round 可先在明确 development 数据上完成实现 canary，再
   seal 全新 holdout；development/holdout 身份必须在 plan 冻结，不能看过
   candidate holdout 后降格成 scratch。
3. 不为每个代码 slice、失败单测或离线模型候选各开一轮。只有跨过 evidence
   trigger 才升级；升级发生在新执行/新结论之前。
4. repository-native evidence workflow 可按 plan 写 `memory/`、`results/` 和
   必要实现面；这不扩大当前手稿线对其他 `paper/<line>` 的写权限。

### Evidence lane: Round 生命周期 (步骤)

1. **领号**: manuscript evidence uses
   `reserve_round.py --strict-no-active --line <line-id> --write-plan-stub`;
   the recorded `manuscript_line` permits one active round per line while an
   explicit `null` remains a repository-global lock. 收尾前
   `reserve_claim.py --round R<N>` — claim id 必须先于 feed 存在
   (feed 内联数字要挂它)。ID 永不手挑。
2. **plan**: `memory/rounds/R<N>/plan.md` — 冻结契约 (什么变/什么固定)、
   预注册判定树、scope_limits、资产保护清单。caveman Chinese。生命周期
   状态只住 YAML frontmatter 的 `state`; R291+ 禁止在正文再写 `Status`。
3. **preflight**: `python memory/tools/round_preflight.py R<N>` —
   exit 2 = BLOCK, 修完再跑。
4. **执行**: 影响结论的识别/筛选/判定逻辑全部进 `probes/`; 可复用
   implementation 进 `src/andes_rl_kundur/`, `scripts/` 只做稳定 execution
   adapter (完整 seam 与 lifecycle 见 `docs/repo-hygiene/executables.md`);
   正式评估 seal-before-trace、产物不可变、逐文件 .sha256。
   ANDES 只能 WSL，且维护中的入口必须经 scratch launcher 运行：
   `/home/wya/andes_venv/bin/python scripts/andes_scratch.py <entrypoint> ...`。
   它把 ANDES 的 `kundur_full_out.*` 留在 `tmp/andes/`，禁止把仓库根目录
   当仿真工作目录；并行 shard 仍共享同一 seal 和仓库绝对结果路径。
   对任何正式 ANDES/WSL 执行，plan 还必须有 `## Formal launch contract`，
   明写 `formal_entry`、`rehearsal_command`、`rehearsal_scope`、
   `rehearsal_checks`、`wsl_python_processes` 与
   `native_threads_per_process`。R339+ 还必须声明 `capacity_evidence`、
   `host_process_budget`、`other_reserved_processes`；并发数没有固定常数，
   但本任务进程数与其他执行中论文线预留数之和不得超过实测整机预算。
   `round_preflight.py` 对缺项、超出当次整机预算或
   原生线程不等于一直接 BLOCK。实现完成且 seal 之前，必须实际执行
   `rehearsal_command`，让它走 formal entry 的 **same pre-attempt
   verification path**，覆盖 source/parent hash、installed package、
   installed case 与 output absence，但不得创建 formal attempt 或正式结果。
   a scientific canary does not satisfy this rehearsal；canary 与正式入口
   可以共享底层检查，但不能跳过正式入口自己的前置路径。rehearsal 输出及其
   所对应源码必须进入 seal。seal 后若仍在 formal attempt 创建前失败，本轮
   只能 aborted；修复必须领后继 round、重新 preflight 与重新 seal，不能原地
   补丁后重试。
5. **收尾** (严格顺序):
   a. 结果归档清点: 每个结论承载 JSON 有 `.sha256`; 在
      `results/MANIFEST.md` 登记 result root、决策文件摘要与 archive
      状态。没有私有第二副本时必须写 `LOCAL-ONLY`，不得称为 durable archive。
   b. feed + publication gate (契约见 §3 与
      `skills/kundur-round/references/publication-gate.md`)；先写 canonical
      feed，再让两个 auditor 审同一份 feed，审核明细仍只进对话或 `tmp/`
   c. claim registration card (形态见 CLAUDE.md "写 claim 的时机与形态")。R281+
      verified finding/correction 必须含结构化 `evidence_refs`
      (`path` + RFC 6901 `locator` + whole-file `sha256` + `role`)。
   d. `feed_check.py`：claim 卡已经收敛到审核允许的措辞并回指 feed 后，运行
      `python memory/tools/feed_check.py <feed>`
   e. verdict 骨架 (模板 `memory/rounds/_TEMPLATE_VERDICT.md`)
   f. programme 问题若关闭: 块归档 `memory/RESEARCH_PROGRAM_CLOSED.md`,
      `priority_questions` 回 []
   g. 若 feed 属于手稿线: 把 `CLM-NNNN -> feed` 加入该线
      `evidence_refs`，刷新当前动作，更新受影响的 `ARTIFACTS.json` 输入；
      feed 不得进入 `required_reading`，实验数字和结论不得复制进 LINE。
      确认语义同步后才刷新 `line-state` 对 feed 目录的哈希。该步不顺手写
      LaTeX/正文/图。
   h. `repo_health.py check --no-baseline` 绿；新增或改动 feed 必须先触发
      `DOCUMENT_INPUT_DRIFT`，然后经 g 的显式 acknowledgement 清除
   i. `close_round.py R<N> completed`；R281+ 会重新执行 feed gate，不能只改
      `plan.md`。R291+ 只要 feed 指向本轮 results，还会要求 MANIFEST 条目。
   j. `validate.py` 绿 → `render.py` → `"$DAIMON_USER_PYTHON" -m pytest tests -q` 绿
   k. **给 PI 的话原文贴进对话** (ADR-0003/0011); 从 R317 起只贴三段
      完整人话，不在前后追加技术复盘；指向文件不算交付

完成判据: validate 绿、round state=completed、三段人话已出现在对话里、
publication gate 无未决硬项、repo health 无 navigation freshness finding、
无事实同时住在两个 ledger 家里。

## 3. Feed 契约 (参考)

feed 是原料, 供后续起草会话翻成论文正文; 人类可读性不在目标内。
一切规则服务一个性质: 起草者两跳取到任何事实 (report → pointer →
source), 且任何事实不遇见第二遍。

R281–R286 feed 头部所写的 `experiment-report` 是历史名称; 当前不存在
独立 skill, 本节是唯一契约。不要为该旧名称再建第二份规则。

### 单一真源分配表

每个实验事实只住一个家, 别处一律指针:

| 家 | 放 | 不放 |
|---|---|---|
| results JSON / traces | 全部测量数字、守卫行、哈希 | 解释 |
| **feed** | 解释、有界结论、手稿映射、头条数字 (每个挂 claim id) | 数据表、守卫明细、逐格转储 |
| claim 卡 | 分类判定 + 主头条数字对 + 范围短语 + 结构化 evidence_refs | 每级表格、位置子表、守卫细节 |
| verdict.md | 技术骨架 + feed 指针；给 PI 的话是三段独立人话层 | 分析、数字表；人话层不放专业名称、编号和过程数字 |
| STATE.md | 无 — render.py 自动渲染, 永不手改 | — |

论文要引的数字设计内存两份 (results 为源, feed 为取料面); 第三份是
fork, 删掉。

### 位置与语言

- 有手稿线: `paper/<line>/reports/<slug>.md` (当前线
  `paper/sci_upgrade_survey/reports/`); 无手稿线: `results/<run>/FEED.md`。
- 英文 (喂英文论文); 用户显式语言要求优先。

### 节契约 (按序)

1. **Identity** — round/claim id、日期、commit、脚本、seal/合约哈希。
   完成判据: 每个路径在盘上可解。
2. **Frozen setup** — 什么固定什么变, 指契约文件; ≤5 行。
3. **Observations** — 每条一个子弹: 解释过的发现 + 指针
   (`path:line` / JSON 字段 / claim id)。内联只允许论文会引的头条
   数字, 且每个挂 claim id; 其余数据留在 results 文件里被指。
4. **Conclusions** — 有界陈述, 每条标证据等级 (analytic > linearized
   small-signal > sealed-bank time-domain > self-evaluated); 措辞强度
   不越级。
5. **Limits** — 范围正面陈述 ("covers X only; Y untested"), 含每个
   预注册失败 flag。
6. **Publication gate** — 证据审计、领域审计、外部语境状态、claim
   disposition、allowed claim、stay-out; 详细流程与固定字段见
   `skills/kundur-round/references/publication-gate.md`。
7. **Manuscript mapping** — 每条 observation 映射到目标节/图, 或给
   明确 stay-out 理由。
8. **Follow-up pointers** (可选, 最后) — 只放指针，不持任务状态。pending
   必须指向 `Q-NNNN` 或当前 `LINE.md`; resolved 标 `resolved-by` 回指后续
   round/claim/feed；unauthorized 明写边界。

### 规则

- 指针优先: 事实已住在 claim / verdict / results 里就指, 重述即 fork。
- 写陈述不写叙述: 无动机散文、无过渡、无简报腔。
- 密度帽两页; 超了说明抄了数据, 回到指针。

### 完成判据

每个路径可解、每个内联数字挂 claim id、每条 observation 有手稿映射或
stay-out、publication gate 无 `FAIL` / `DEEP-RESEARCH-REQUIRED` 未决项、
任何数据两跳可达。`feed_check.py` 只对路径、claim 绑定、映射和 gate
字段做确定性判定；“同一事实没有在 claim 卡、verdict 正文和 feed
重复居住”由 evidence audit 做语义审查，不能把脚本通过误报为该项已通过。

### 文档预算

一次 round 的新持久 prose 默认只有 plan、feed、claim 注册卡、verdict。
学术审核明细留在对话或 `tmp/`; 只有转化为既有实体类型
(question/claim/ADR/issue/注册手稿资产) 才持久化。原始表、trace、hash
留在 results, 不为每次解释另建 Markdown。

从 R291 起，`validate.py` 硬限制 claim statement ≤1800 UTF-8 bytes、
verdict ≤80 个非空行。超限内容应移到 feed 或 machine JSON，而不是扩大
预算。`feed_check.py` 同时要求本轮 machine JSON 的合法 sidecar 和
`results/MANIFEST.md` 条目。Note 只索引外部来源；未决工作必须进入
Question 或当前手稿 `LINE.md`。

## 4. 护栏 (硬; 操作清单 — rationale 各见其源)

- 先 probe 后训练; 用 kill/pivot 门避免纯算力搜索 (政策:
  `memory/RESEARCH_PROGRAM.md` "Autonomous research policy" / "Kill and
  pivot rules")。
- 固定拓扑上不追 algorithm-only SOTA (R86 结构性 plateau, CLM-0148/0149)。
- paper-cited 资产 (`base_env.py`、`andes_vsg_env_v4.py`、`train.py`、
  `paper_grade_axes.py`) 只在新 round + claim 里改 (原则:
  CLAUDE.md 工程原则 3)。
- baseline 只用 `baselines.py` 查 measured, 不估 (原则: CLAUDE.md
  工程原则 2)。
- 单机 WSL Python 并行上限只以 CLAUDE.md 为数字真源；plan 的 Formal launch
  contract 必须计入 launcher、child 与 process-pool worker，不能只写逻辑 shard
  数。每个进程的原生数值库线程固定为一；不同资料分区、拟合/验证或其他封存
  边界仍串行。
- 语言: plan 与 verdict 技术骨架可用紧凑中文；question/claim/feed 用英文。
  从 R317 起，PI 话只写“发生了什么、这说明什么、下一步做什么”三段完整
  自然中文。禁英文、缩写、仓库编号、文件名、代码名和明显专业词；数字只在
  直接表达改善、恶化或是否及格时保留。技术证据不删减，留在 feed、claim、
  results 与 verdict 技术骨架 (模板: `memory/rounds/_TEMPLATE_VERDICT.md`)。

## 5. 手稿线 (步骤)

1. 每篇文章建立一个注册 delivery root、`LINE.md` 与 `ARTIFACTS.json`。
   `LINE.md` 只保存该文的状态、优先级、读写作用域、venue 状态、当前动作和
   指针。Deep Research/venue 决策用 `path#locator` 的 `decision_refs`；
   实验证据用 `CLM-NNNN -> feed` 的 `evidence_refs`。不得复制源文结论或数字。
2. 默认用 `session_context.py` 选择最高优先级 active 线；明确处理另一篇时用
   `python memory/tools/session_context.py --json --line <line-id>`。
3. 只写当前线 `scope.write_roots`。`scope.shared_read_roots` 中的会议稿、
   results、memory 与跨线调研仅可读取；跨线写入需要单独选择并授权目标线。
4. 持久化 Deep Research、审稿汇总、决策、草稿或图前先登记到该线
   `ARTIFACTS.json`。过程输出默认住 `tmp/<line>/`，不登记每个 reviewer 的
   中间报告。
5. 每种 purpose 只有一个 active canonical；新版本用 `supersedes` 替换旧条目。
   时间敏感条目必须有 `review_after`，过期或输入漂移后不得当当前依据。
6. 有 `experiment-feeds` 的线必须由 active `line-state` 对整个 feed 目录做
   `input_hashes` 快照。新 feed/旧 feed 改动后冷启动必须先进入
   `manuscript-refresh`；最新 feed 必须加入 `evidence_refs`，禁止放进
   `required_reading`，也禁止只改哈希而不核对 LINE 当前动作和受影响
   artifact 输入。
7. Venue Gate 分三次：问题与贡献成形后 shortlist；证据与故事稳定后 lock；
   投稿前 refresh。作者/PI 拥有最终期刊决策。

完成判据: 当前线唯一、write scope 无跨线、持久文档均已登记、venue 状态可解释、
其他论文线没有被顺手修改。

## 指针 (仓库文件, 各持其事实)

- `CLAUDE.md` — 工程原则、memory schema、ledger 形态规则、工具目录、
  代码约定
- `memory/rounds/_TEMPLATE_VERDICT.md` — verdict 骨架模板 (validate.py
  强制节)
- `memory/tools/*.py` — 自文档 (docstring 含 motivation/usage/失败模式)
- `skills/kundur-round/references/research-skill-adapter.md` — 全局研究
  skill 在本项目中的唯一适配层
- `paper/<line>/LINE.md` — 各手稿线自己的状态与作用域
- `paper/<line>/ARTIFACTS.json` — 各手稿线的持久文档生命周期清单
