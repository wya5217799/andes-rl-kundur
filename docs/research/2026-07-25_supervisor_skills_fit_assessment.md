# Supervisor-Skills 对 `andes-rl-kundur` 的适配性审计

**日期**：2026-07-25  
**审计对象**：HKUSTDial/Supervisor-Skills  
**固定版本**：[`aff5de9e5b902df0ef51e955d4c78b22793d763a`](https://github.com/HKUSTDial/Supervisor-Skills/tree/aff5de9e5b902df0ef51e955d4c78b22793d763a)  
**本项目目标**：TPWRS-oriented automatic research programme  
**审计性质**：采用前只读评估；没有安装 skill、没有创建 research round/claim、没有运行 ANDES。

## 结论

**有帮助，但只适合选择性采用，不适合整套接管本项目。**

更准确地说，Supervisor-Skills 是一组研究检查表、写作护栏和少量
Draw.io 工具，不是具有长期状态、实验调度、证据账本和领域判断能力的
“自动博导”。它最值得复用的是：

1. `deep-research` 的多视角检索、逐条引用核验和证据强度校准；
2. `paper-writer` 的 Evidence Map 和“模型记忆不是证据”规则；
3. `idea-evaluator` 的 fatal-flaw 早停，但只作为反方审稿，不作为选题
   oracle；
4. `paper-polish` 的含义保真；
5. P4 稿件阶段的补充审查和图形叙事检查。

它不能替代本项目已有的：

- `memory/RESEARCH_PROGRAM.md` 中的 TPWRS north star、phase gate 和
  kill/pivot rule；
- `research_goal.py` 的单一 programme-ranked objective；
- round/claim 原子编号、sealed bank、measured provenance；
- `round_preflight.py`、`dual_metric_lint.py`、`validate.py`、`render.py`；
- 电力系统稳定性、安全性、拓扑 OOD、跨仿真器/HIL 证据标准。

因此推荐：

> **保留现有研究治理为唯一权威层；先不全量安装，只对
> `deep-research` 做一个固定范围、可证伪的 A/B 试点。**

## 它实际是什么

固定版本包含 11 个 skills。上游自己的读者指南将它们分成技术论文、
benchmark/evaluation 论文和横向工具三组；截至本次审计，上游
changelog 明确说明旧 plugin 目录只是遗留结构，**从未存在 plugin
manifest**。所以这不是一个可独立运行的 supervisor service，也不是
具有统一状态机的 Codex plugin。

一手来源：

- [11 个 skills 及工作流](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/README.en.md)
- [v2.1 layout 与“no plugin manifest ever existed”](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/CHANGELOG.md#L41-L50)
- [顶层 Quick Start](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/README.en.md#L185-L191)

大部分内容是 `SKILL.md` 和按需加载的 Markdown references。只有
`drawio-reconstruction` 含实质执行脚本，并依赖 Python、可选 Pillow
和 Draw.io Desktop/CLI。

## 对 11 个 skills 的分组判断

| Skill | 本项目适配性 | 当前建议 | 关键原因 |
|---|---|---|---|
| `deep-research` | 高 | **现在试点** | 冻结 RQ、多视角搜索、引用核验、MECE 综合和反方检查可补强文献工作 |
| `paper-writer` | 高但阶段未到 | **P4 再启用** | Evidence Map 与 claim provenance 高度一致，但当前 P0 不应提前包装论文故事 |
| `paper-polish` | 高但阶段未到 | **P4 再启用** | 含义风险编辑显式列出，适合最终稿语言层 |
| `idea-evaluator` | 中 | **仅作反方审稿** | fatal-flaw 短路有价值；1–10 分与 verdict 阈值未经验证，不能放行/终止 programme |
| `tech-paper-template` | 中 | **P3/P4 使用** | problem→mechanism→module→contribution 对齐有用，但不应反向塑造尚未成熟的证据 |
| `pre-submission-reviewer` | 中低 | **TPWRS 定制后再用** | 能补充语言/结构检查，但包含明显 CS/会议模板偏置和任意严重性规则 |
| `figure-designer` | 中 | **按需使用** | 可帮助方法图和结果图叙事；不能替代可复现绘图与物理信息表达 |
| `drawio-reconstruction` | 低到中 | **有参考图时单独用** | 适合重建编辑图，不改善研究问题、实验或统计有效性 |
| `intro-drafter` | 低到中 | **不作为默认 Intro 模板** | 六段式和 15–25 引文建议偏 AI/CS conference，不等同 TPWRS 结构 |
| `benchmark-paper-template` | 低 | **当前不采用** | 本项目目标是控制方法与系统 insight，不是新 benchmark 论文 |
| `vibe-research-workflow` | 低 | **不采用** | 与 AGENTS/CLAUDE/research programme 高度重复，容易形成第二套治理 |

## 最有价值的部分

### 1. `deep-research`

它要求先冻结 2–3 个可回答的研究问题，再从 mainstream、critics、
adjacent fields、methodology、application/policy 等 3–5 个视角独立
搜索；每条候选引用必须先验证存在性，再检查转述是否超过摘要/全文
能够支持的范围。无法确认的来源不得进入报告。

这比普通“搜一些相关论文”更强，尤其适合本项目后续的：

- topology-generalising residual control 文献地图；
- safety projection、stability certificate 与 RL control 的交叉文献；
- cross-simulator/HIL evidence 的最低标准；
- TPWRS 审稿人可能提出的反方证据。

来源：

- [`deep-research/SKILL.md`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/deep-research/SKILL.md)
- [citation verification protocol](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/deep-research/references/citation-protocol.md)
- [quality gates](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/deep-research/references/quality-gates.md)

### 2. `paper-writer` 的 Evidence Map

上游将证据分为用户提供的全文/数据、摘要、metadata、有限的领域常识
和不可使用的 model memory，并要求每项来源同时记录“能支持什么”和
“不能支持什么”。这与本项目的 CLM、measured provenance 和 conclusion
boundary 很匹配。

若未来采用，不应创建一套平行的 `E1/E2/...` 永久账本。建议直接映射：

| Supervisor-Skills 概念 | 本项目唯一落点 |
|---|---|
| Evidence Map ID | `CLM-NNNN`、raw trace、summary JSON 或固定文献 |
| Evidence level | claim trust + provenance + source type |
| Contribution-to-evidence | manuscript claim → CLM/figure/table |
| Evidence gap | open `Q-NNNN` 或明确从稿件删除 |
| Final mode blocker | `validate.py` + manuscript-specific audit |

来源：

- [`paper-writer/SKILL.md`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/paper-writer/SKILL.md)
- [evidence discipline](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/paper-writer/references/evidence-discipline.md)

### 3. `idea-evaluator` 的 fatal-flaw 短路

“先找致命缺陷，再评分”的顺序是正确的。特别是“用户已有数据已经否定
核心机制时，直接 Reject and Pivot，不再用高分维度装饰结论”，与 R265
的负 verdict 和本项目 kill/pivot 规则一致。

但其 Higher/Faster/Stronger/Cheaper/Broader 五维和 Strong Accept 阈值是
启发式模板，不是经校准的 TPWRS 选题指标。若使用，应替换为：

1. physics/objective validity；
2. mechanism identifiability；
3. topology OOD generalisation；
4. safety/stability；
5. statistical and provenance rigor；
6. simulator/HIL fidelity；
7. matched compute/data budget。

其输出只能作为 programme question 的反方意见；正式选题仍由
`RESEARCH_PROGRAM.md` 排名和 `research_goal.py` 决定。

来源：

- [`idea-evaluator/SKILL.md`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/idea-evaluator/SKILL.md)
- [fatal flaws](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/idea-evaluator/references/fatal-flaws.md)

## 与现有自动研究流程的边界

### 保持唯一权威

| 决策/状态 | 唯一权威 | 外部 skill 的允许角色 |
|---|---|---|
| 当前 programme objective | `research_goal.py` | 不得另选题 |
| active round | `reserve_round.py --strict-no-active` | 不得创建平行任务状态 |
| claim ID 与测量结论 | `reserve_claim.py` + `memory/claims` | 只能引用，不得自建编号 |
| 实验停止/转向 | round plan + programme kill/pivot | 只能提出风险，不得覆盖预注册门 |
| sealed evidence | bank bytes/hash + provenance | 不得把文献/写作评分当实验结果 |
| state oracle | `STATE.md`（由 `render.py` 生成） | 不得直接编辑 |
| scientific verification | tests、preflight、lint、validate、render | prompt integrity gate 只能是补充 |

### 避免术语冲突

`deep-research` 的 literature RQ 不应创建为 programme `Q-NNNN`，除非它
确实成为下一轮可执行的不确定性。临时文献问题可写在
`docs/research/*.md`，并明确标为 literature RQ。

`paper-writer` 的 evidence map 不应复制 claim ledger。稿件中的每个数字、
效果和结论应回链到现有 CLM、trace 或 summary。

`idea-evaluator` 的 Accept/Reject 不得覆盖 round verdict。它只能在预注册
之前暴露风险。

## 不适合直接照搬的部分

### 1. 学科与 venue 偏置

上游方法论和案例主要来自 SIGMOD、VLDB、ICML、NeurIPS、ICLR。
`pre-submission-reviewer` 虽增加了“STEM/engineering”路由，但没有
TPWRS、电力系统暂态仿真、控制稳定性、模型/装置保真度、故障/时延、
拓扑 OOD、HIL/RTDS 等专门检查。

因此它最多是语言与叙事的第二审稿人，不能判断 TPWRS scientific
readiness。

### 2. 将风格偏好误升为严重性规则

上游 reviewer 将以下内容写成普适审查规则：

- Introduction 六段链；
- 段落不超过 10 行；
- em-dash 默认 MAJOR；
- 最终图必须 vector；
- 没有 real-world running example 可被视为 CRITICAL；
- 固定 banned-vocabulary 数量阈值。

这些可作为清单，但不是 IEEE/TPWRS 官方接收标准，也不应与缺少 stability
evidence、baseline 不公平或 OOD claim 无 unseen graph 等科学缺陷同级。

来源：

- [`pre-submission-reviewer/SKILL.md`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/pre-submission-reviewer/SKILL.md)

### 3. 定量分数没有效度证据

上游提供 1–10 idea 分数、最终稿 1–10 分和三档 verdict，但仓库没有给出
这些分数与论文正确性、接收率或研究影响之间的校准实验。GitHub stars、
作者经验和展示案例都不能替代这种效度证据。

### 4. 写作工具可能过早优化故事

本项目当前是 `P0_evidence_repair`。若现在启用 intro/paper-writing
全流程，容易把有限结果组织成一个看似完整的故事，反而削弱“correctness
and objective validity first”。写作 skills 应延后到 P4，或只用于记录
已冻结的负/正证据。

## 许可证与集成方式

上游根许可证是 **CC BY-NC-SA 4.0**，而本项目是 MIT。若将整套 skill 或
其改编内容直接复制进本仓库，可能引入 attribution、non-commercial 和
share-alike 边界。若干旧 skill frontmatter 仍写 CC-BY-4.0，和根许可证
不一致；`drawio-reconstruction` 子目录另有 MIT License。

这不是法律意见。工程上应采取保守策略：

1. 不 vendor 整套仓库；
2. 如需试用，在个人 Codex skill 目录逐个安装；
3. 固定 commit SHA，不跟随浮动 `main`；
4. 保留许可证和 attribution；
5. 若计划复制、改编或随 MIT 项目发布，先向维护者确认具体文件许可。

来源：

- [根 LICENSE](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/LICENSE)
- [CONTRIBUTING 的许可声明](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/CONTRIBUTING.md)
- [Draw.io 子目录 MIT LICENSE](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/drawio-reconstruction/LICENSE)

## 安全与维护审计

多数 skills 是提示文本，未发现隐蔽下载器、网络请求代码、删除逻辑或
凭据读取。`deep-research`、`paper-writer` 会要求外部检索并读取研究
材料，因此仍需遵守未公开论文、数据和日志的保密边界。

`drawio-reconstruction` 是主要执行面：

- manifest 和导出脚本会写文件、创建目录、启动 Draw.io；
- batch verifier 信任 manifest 中的路径；
- exporter 会从参数、`DRAWIO_PATH`、常见安装目录或 `PATH` 解析可执行
  文件；
- 不应对不可信 manifest、路径或环境变量运行。

上游 CI 只做 SKILL 结构和 shared-reference 同步，没有 skill 输出质量
回归、Draw.io 集成测试、恶意路径测试或安全扫描。因此“lint clean”不能
证明研究质量或运行安全。

来源：

- [CI workflow](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/.github/workflows/lint.yml)
- [Draw.io batch verifier](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/drawio-reconstruction/scripts/batch_verify.py)
- [Draw.io exporter](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/skills/drawio-reconstruction/scripts/export_drawio.py)

## 本地复现

审计将上游固定到：

```text
aff5de9e5b902df0ef51e955d4c78b22793d763a
```

检查结果：

| 检查 | 结果 |
|---|---|
| Python helper `compileall` | clean |
| 默认 Windows 中文 locale 运行 `lint_skills.py` | 失败；多个 UTF-8 文件被错误报告为不可解码 |
| 默认 locale 运行 `check_shared_sync.py` | `UnicodeDecodeError` |
| 设置 `PYTHONUTF8=1` 后结构 lint | **11 skills clean** |
| 设置 `PYTHONUTF8=1` 后共享引用同步 | **5 copies in sync** |

根因是两个脚本使用 `Path.read_text()` 而未显式指定
`encoding="utf-8"`。这是 Windows 可移植性缺陷，不是 Markdown 内容损坏。
若未来采用，应使用 UTF-8 mode 或在本地包装器中固定编码。

来源：

- [`lint_skills.py`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/scripts/lint_skills.py)
- [`check_shared_sync.py`](https://github.com/HKUSTDial/Supervisor-Skills/blob/aff5de9e5b902df0ef51e955d4c78b22793d763a/scripts/check_shared_sync.py)

## 最小可证伪试点

不要先全量安装。先测试一个明确问题：

> 在不修改 programme question、claim ledger 和实验计划的前提下，
> `deep-research` 是否能显著改善现有 VSG/RL publication landscape 的
> 覆盖率与引用正确性？

### 输入冻结

- 基线文档：
  `docs/research/2026-07-24_rl_vsg_publication_landscape.md`；
- 固定上游 commit：
  `aff5de9e5b902df0ef51e955d4c78b22793d763a`；
- 固定 2–3 个 literature RQ；
- 只允许使用论文、期刊/会议官网、标准、官方代码等一手来源；
- 不改 `Q-NNNN`、`CLM-NNNN`、round 或 `STATE.md`。

### 对照

使用同一 brief 各跑一次：

1. 当前本地 `research` skill；
2. 上游 `deep-research`。

由盲审清单比较：

- 新增且真正相关的一手来源数；
- 找出的实质 citation/claim 错误数；
- 覆盖的反方证据和方法学盲点数；
- 不可核验或错误引用数；
- 总时间、检索调用和上下文成本；
- 结论是否越过证据强度。

### 通过门

建议只有同时满足以下条件才保留：

1. `0` fabricated/unverifiable citations 进入正文；
2. 至少发现 `1` 个实质错误，或新增 `3` 个会改变 landscape 判断的高价值
   一手来源；
3. 没有创建平行 research state 或覆盖 programme objective；
4. 额外成本不超过基线的 `2x`；
5. 产物能直接回链到本项目文献和 claim，而不是只增加篇幅。

否则结论应是“不安装，继续使用现有 research workflow”。

## 最终采用建议

### 现在

- 只评估 `deep-research`；
- `idea-evaluator` 仅在新增 programme question 前作为一次反方检查；
- 不安装整套，不复制进 MIT 仓库；
- 不允许外部 skill 预留 round/claim 或改变 stopping condition。

### P3/P4

- 把 `tech-paper-template` 用作 claim→method→experiment 对齐表；
- 把 `paper-writer` Evidence Map 映射到现有 CLM/provenance；
- 使用 `paper-polish` 做含义保真的语言层；
- 将 `pre-submission-reviewer` 改造成 TPWRS-specific checklist 后再用；
- 图形工具只负责表达，不负责证明科学结论。

### 永久不变的优先级

```text
correctness and objective validity
-> residual mechanism
-> topology generalisation
-> safety/stability
-> cross-simulator/HIL
-> manuscript
```

Supervisor-Skills 可以加强这个链条中的检索、检查和表达，但不能改变其
顺序，也不能代替可复现的物理证据。
